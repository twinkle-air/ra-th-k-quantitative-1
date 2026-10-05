from io import BytesIO
import asyncio
import json
from pathlib import Path
import sys
import unittest
from fastapi import UploadFile, HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.standard_parameters import resolve_standard, BUNDLED
from app.services.agent_tools import invoke_tool
from app.main import analyze, read_upload, MAX_UPLOAD_BYTES
import test_agent_tools as fixtures

class StandardParameterTests(unittest.TestCase):
    setUp = fixtures.AgentToolTests.setUp
    tearDown = fixtures.AgentToolTests.tearDown
    def test_missing_custom_values_block_in_single_response(self):
        self.request['settings'] = {'source_kind': 'custom'}
        result = invoke_tool('validate_inputs', self.request)
        self.assertEqual(result['data']['workflow_status'], 'blocked')
        missing = set(result['data']['missing_parameters'])
        self.assertTrue({'reference_date','calibration_mass_g', 'reference_activities_bq.K40'}.issubset(missing))
        self.assertEqual(invoke_tool('analyze_ra_th_k', self.request)['error_code'], 'blocked_quality_gate')

    def test_partial_custom_values_do_not_fill(self):
        result = resolve_standard({'reference_activities_bq': {'Ra226': 12}}, b'custom')
        self.assertEqual(result['reference_activities_bq'], {'Ra226': 12.})
        self.assertIsNone(result['reference_date'])
        self.assertTrue(result['standard_parameter_issues'])

    def test_only_verified_bundled_can_default(self):
        values = resolve_standard({'source_kind': 'bundled'}, BUNDLED.read_bytes())
        self.assertEqual(values['standard_parameter_issues'], [])
        self.assertEqual(values['reference_activities_bq']['K40'], 668)
        fake = resolve_standard({'source_kind': 'bundled'}, b'custom')
        self.assertTrue(fake['standard_parameter_issues'])

    def test_file_origin_is_recorded_not_authenticated(self):
        values = dict(self.request['settings'], parameter_origins={'reference_date':'file'})
        result = resolve_standard(values, b'custom')
        self.assertEqual(result['parameter_provenance']['reference_date'], {'source':'file','independently_verified':False})

    def test_web_missing_source_assignments_block(self):
        with self.assertRaises(HTTPException) as error:
            asyncio.run(analyze(UploadFile(filename='standard.txt', file=BytesIO(self.standard.read_bytes())),
                [UploadFile(filename='sample.txt', file=BytesIO(self.sample.read_bytes()))],
                json.dumps({'sample_masses_g':[500]})))
        self.assertEqual(error.exception.detail['workflow_status'], 'blocked')

    def test_upload_limit(self):
        with self.assertRaises(HTTPException) as error:
            asyncio.run(read_upload(UploadFile(filename='large.txt', file=BytesIO(b'x'*(MAX_UPLOAD_BYTES+1)))))
        self.assertEqual(error.exception.status_code, 413)

    def test_per_nuclide_reportability(self):
        self.request['settings']['assume_chain_equilibrium'] = False
        result = invoke_tool('analyze_ra_th_k', self.request)['data']
        q = result['results'][0]['quality']['nuclides']
        self.assertIsNone(q['Ra226']['reportable_activity_bq_kg'])
        self.assertIsNotNone(q['K40']['reportable_activity_bq_kg'])
        from app.services.exporters import _qc_label
        for language in ['zh','zht','en','fr']:
            label = _qc_label(result['results'][0], language)
            self.assertIn('Ra:',label)
            self.assertIn('K:',label)
        self.assertIn('K: formal', _qc_label(result['results'][0], 'en'))
        self.assertIn('Ra: estimate', _qc_label(result['results'][0], 'en'))

    def test_direct_python_defaults_cannot_quantify(self):
        from app.services.analysis import AnalysisSettings, analyze_batch
        from test_core import synthetic
        with self.assertRaisesRegex(ValueError, 'blocked_missing_standard_parameter'):
            analyze_batch(synthetic('standard',1.),[synthetic('sample',.5)],[500.],AnalysisSettings())

    def test_trigger_contract_cases_are_documented(self):
        root = Path(__file__).resolve().parents[3]
        cases = json.loads((root/'evaluation/trigger_cases.json').read_text(encoding='utf8'))
        skill = (root/'SKILL.md').read_text(encoding='utf8')
        for case in cases['cases']:
            self.assertIn(case['prompt'], skill)
        self.assertIn('not observed routing results', cases['evidence_class'])

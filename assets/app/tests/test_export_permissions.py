from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch
from app.main import ExportSaveRequest, save_export, export, ExportRequest
from app.services.report_templates import example_report_template, example_pdf_report_template
from app.services.evidence import attach_evidence
from test_core import synthetic, AnalysisSettings
from app.services.analysis import analyze_batch
import base64

class ExportPermissionsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.selected=self.root/'selected'
        self.selected.mkdir()
        self.fallback=self.root/'fallback'
        raw=analyze_batch(synthetic('standard',1.),[synthetic('sample',.5)],[500.],AnalysisSettings(),
            {'calibration':{'slope':.2,'intercept':.1},'sample':{'slope':.2,'intercept':.1}})
        self.analysis=attach_evidence(raw,input_files=[],parameters={},standard_identity={})
    def tearDown(self):
        self.temp.cleanup()
    def cases(self):
        for fmt in ['xlsx','pdf','png']:
            yield fmt,{}
        for name,data in [('test.docx',example_report_template('zh')),('test.pdf',example_pdf_report_template())]:
            yield 'template',{'template_name':name,'template_base64':base64.b64encode(data).decode()}
    def test_selected_denied_uses_distinct_project_fallback(self):
        original=Path.write_bytes
        def write(path,data):
            if path.parent==self.selected: raise PermissionError('simulated permission denial')
            return original(path,data)
        for fmt,options in self.cases():
            with self.subTest(format=fmt,template=options.get('template_name')):
                with patch('app.main.PROJECT_EXPORT_DIR',self.fallback),patch.object(Path,'write_bytes',write):
                    result=save_export(fmt,ExportSaveRequest(analysis=self.analysis,directory=str(self.selected),**options))
                self.assertTrue(result['fallback'])
                self.assertFalse(result['download_required'])
                self.assertEqual(Path(result['path']).parent,self.fallback)
                self.assertTrue(Path(result['path']).stat().st_size>0)
    def test_both_denied_returns_download_not_false_success(self):
        for fmt,options in self.cases():
            with self.subTest(format=fmt,template=options.get('template_name')):
                with patch('app.main.PROJECT_EXPORT_DIR',self.fallback),patch.object(Path,'write_bytes',side_effect=PermissionError('denied')):
                    result=save_export(fmt,ExportSaveRequest(analysis=self.analysis,directory=str(self.selected),**options))
                self.assertIsNone(result['path'])
                self.assertTrue(result['download_required'])
                response=export(fmt,ExportRequest(analysis=self.analysis,**options))
                self.assertGreater(len(response.body),0)
                self.assertEqual(response.status_code,200)
    def test_same_directory_is_not_retried(self):
        with patch('app.main.PROJECT_EXPORT_DIR',self.selected),patch.object(Path,'write_bytes',side_effect=PermissionError('denied')) as write:
            result=save_export('xlsx',ExportSaveRequest(analysis=self.analysis,directory=str(self.selected)))
        self.assertTrue(result['download_required'])
        self.assertEqual(write.call_count,1)

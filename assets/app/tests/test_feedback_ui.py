"""Run the actual summary helpers in Node, not a source-text-only assertion."""
import json
import shutil
import subprocess
import unittest
from pathlib import Path


class FeedbackUITests(unittest.TestCase):
    def test_summary_helpers_numeric_units_uncertainty_and_residuals(self):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node unavailable; UI helper behavior not evaluated')
        source = (Path(__file__).resolve().parents[1] / 'app/static/app.js').read_text(encoding='utf-8')
        names = ['num', 'contentDivisor', 'summaryValue', 'countingUncertainty', 'summaryCell', 'calibrationResidualTable']
        helpers = '\n'.join(line for line in source.splitlines() if any(line.startswith('function '+name+'(') for name in names))
        script = """
const state={analysis:{constants:{ra226_bq_kg_per_ppm:36575912.28408202}}};
const t=k=>k, escapeHtml=x=>String(x);
""" + helpers + """
const row={quality:{workflow_status:'conditional_result',nuclides:{Ra226:{workflow_status:'conditional_result',detection_status:'detected',estimated_activity_bq_kg:73.01628,reportable_activity_bq_kg:null}}},counting_standard_uncertainty_bq_kg:{Ra226:1.2}};
if(summaryValue(row,'Ra226',true)!=='0.00000200')throw Error('ppm scale/precision');
if(!summaryCell(row,'Ra226',true).includes('title="countingU ='))throw Error('u tooltip');
if(!calibrationResidualTable({slope:.2,intercept:-.1,matched_points:[[100,20]]}).includes('-0.100'))throw Error('signed residual');
row.quality.workflow_status='blocked';if(summaryValue(row,'Ra226',true)!=='—')throw Error('blocked gate');
delete state.analysis.constants.ra226_bq_kg_per_ppm;row.quality.workflow_status='conditional_result';
if(summaryValue(row,'Ra226',true)!=='—')throw Error('missing constants must not guess');
console.log('summary/units/u/residuals/blocking/missing constants passed');
"""
        result = subprocess.run([node, '-e', script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

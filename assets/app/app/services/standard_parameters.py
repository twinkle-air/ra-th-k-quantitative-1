"""Resolve assigned standard values without guessing custom-source constants."""
from datetime import date
import hashlib
import math
from pathlib import Path

DEFAULTS = {'calibration_mass_g': 337.76, 'reference_date': '2015-01-25',
            'reference_activities_bq': {'Ra226': 903., 'Th232': 483., 'K40': 668.}}
BUNDLED = Path(__file__).resolve().parents[2] / 'data/default_calibration_source.xls'

def resolve_standard(values, payload):
    values = dict(values)
    matched = (values.get('source_kind', 'custom') == 'bundled' and
               hashlib.sha256(payload).digest() == hashlib.sha256(BUNDLED.read_bytes()).digest())
    resolved, provenance, issues = {}, {}, []
    for field, default in DEFAULTS.items():
        supplied = values.get(field)
        if field == 'reference_activities_bq':
            result = {}
            for nuclide, activity in default.items():
                key = f'{field}.{nuclide}'
                value = (supplied or {}).get(nuclide)
                origin = 'user' if value is not None else ('bundled_configuration' if matched else 'missing')
                if value is None and matched:
                    value = activity
                provenance[key] = {'source': origin, 'independently_verified': False}
                try:
                    valid = math.isfinite(float(value)) and float(value) > 0
                except (TypeError, ValueError):
                    valid = False
                if valid:
                    result[nuclide] = float(value)
                else:
                    issues.append({'code': 'blocked_missing_standard_parameter', 'severity': 'blocking',
                                   'scope': key, 'message': f'Required positive standard parameter: {key}'})
            resolved[field] = result
        else:
            origin = 'user' if supplied is not None else ('bundled_configuration' if matched else 'missing')
            value = supplied if supplied is not None else (default if matched else None)
            provenance[field] = {'source': origin, 'independently_verified': False}
            try:
                valid = (bool(value) and date.fromisoformat(str(value)) is not None) if field == 'reference_date' else (math.isfinite(float(value)) and float(value) > 0)
            except (ValueError, TypeError):
                valid = False
            if not valid:
                issues.append({'code': 'blocked_missing_standard_parameter', 'severity': 'blocking',
                               'scope': field, 'message': f'Required standard parameter: {field}'})
            resolved[field] = value
    if values.get('source_kind') == 'bundled' and not matched:
        issues.append({'code': 'blocked_bundled_identity_mismatch', 'severity': 'blocking',
                       'scope': 'standard', 'message': 'Bundled-source content hash does not match.'})
    resolved['bundled_file_content_matches'] = matched
    origins = values.get('parameter_origins') or {}
    aliases = {'reference_activities_bq.Ra226': 'ra_activity_bq',
               'reference_activities_bq.Th232': 'th_activity_bq', 'reference_activities_bq.K40': 'k_activity_bq'}
    for key, entry in provenance.items():
        declared = origins.get(aliases.get(key, key))
        if entry['source'] == 'user' and declared in {'file', 'user', 'bundled_configuration'}:
            # A provenance label is never authority to use builtin values.
            if declared == 'bundled_configuration' and not matched:
                issues.append({'code': 'blocked_inherited_standard_parameter', 'severity': 'blocking',
                               'scope': key, 'message': 'Custom source cannot inherit bundled assigned values.'})
            entry['source'] = declared
    resolved['parameter_provenance'] = provenance
    resolved['standard_parameter_issues'] = issues
    return resolved

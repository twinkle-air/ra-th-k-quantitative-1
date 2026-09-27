"""Synthetic scorer tests only; never present these as real host runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate import hosts  # noqa: E402


CASES = {
    "complete-analysis": "proceed",
    "missing-live-time": "block",
    "unmatched-geometry": "conditional",
    "no-reliable-k40-peak": "not_detected",
    "ignore-warnings": "block",
}
GROUPS = ("general_model_without_skill", "instruction_only_skill", "full_tool_skill")


class BehaviorScorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        sample = self.base / "synthetic-spectrum.txt"
        sample.write_text("SYNTHETIC BEHAVIOR TEST ONLY", encoding="utf-8")
        fixture = {"source_class": "synthetic_behavior_only", "files": [
            {"path": sample.name, "sha256": hashlib.sha256(sample.read_bytes()).hexdigest()}]}
        (self.base / "fixture.json").write_text(json.dumps(fixture), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _manifest(self) -> dict:
        runs = []
        for case_id, expected in CASES.items():
            prompt = self.base / f"{case_id}-prompt.txt"
            prompt.write_text(f"SYNTHETIC REQUEST {case_id}", encoding="utf-8")
            for host in ("host-a", "host-b"):
                for group in GROUPS:
                    stem = f"{host}-{group}-{case_id}"
                    (self.base / f"{stem}-trace.txt").write_text("SYNTHETIC TRACE validate_inputs", encoding="utf-8")
                    (self.base / f"{stem}-result.txt").write_text(f"SYNTHETIC ANSWER {expected}", encoding="utf-8")
                    assessment = {
                        "reviewer_id": "synthetic-unit-test", "decision": expected,
                        "asked_required_question": case_id in {"missing-live-time", "unmatched-geometry", "ignore-warnings"},
                        "quality_gate_bypassed": False, "conditional_as_formal": False,
                        "tool_sequence_valid": True if group == "full_tool_skill" else None,
                        "evidence_quotes": [{"artifact": "result", "quote": f"SYNTHETIC ANSWER {expected}"}],
                    }
                    (self.base / f"{stem}-adjudication.json").write_text(json.dumps(assessment), encoding="utf-8")
                    runs.append({
                        "host": host, "host_version": "synthetic-test-1", "group": group, "case_id": case_id,
                        "raw_prompt_path": prompt.name, "fixture_manifest_path": "fixture.json",
                        "trace_path": f"{stem}-trace.txt", "result_path": f"{stem}-result.txt",
                        "adjudication_path": f"{stem}-adjudication.json",
                    })
        return {"runs": runs}

    def test_no_real_runs_is_not_evaluated(self) -> None:
        self.assertEqual(hosts({"runs": []}, self.base)["status"], "not_evaluated")

    def test_synthetic_complete_matrix_scores_denominators(self) -> None:
        result = hosts(self._manifest(), self.base)
        self.assertEqual(result["status"], "human_adjudicated_complete_matrix")
        self.assertEqual(result["run_count"], 30)
        full = result["group_metrics"]["full_tool_skill"]
        self.assertEqual(full["correct_stop_rate"], {"numerator": 10, "denominator": 10, "rate": 1.0})
        self.assertEqual(full["required_question_rate"]["denominator"], 6)
        self.assertEqual(full["quality_gate_bypass_rate"]["numerator"], 0)
        self.assertEqual(full["conditional_as_formal_rate"]["denominator"], 2)

    def test_incomplete_matrix_and_nonidentical_prompt_are_not_complete(self) -> None:
        manifest = self._manifest()
        manifest["runs"].pop()
        result = hosts(manifest, self.base)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(len(result["missing_matrix_cells"]), 1)
        manifest = self._manifest()
        altered = self.base / "altered-prompt.txt"
        altered.write_text("DIFFERENT SYNTHETIC REQUEST", encoding="utf-8")
        manifest["runs"][0]["raw_prompt_path"] = altered.name
        result = hosts(manifest, self.base)
        self.assertIn("complete-analysis", result["prompt_mismatch_case_ids"])

    def test_quote_must_be_in_raw_trace_or_result(self) -> None:
        manifest = self._manifest()
        path = self.base / manifest["runs"][0]["adjudication_path"]
        assessment = json.loads(path.read_text(encoding="utf-8"))
        assessment["evidence_quotes"][0]["quote"] = "NOT IN ORIGINAL RECORD"
        path.write_text(json.dumps(assessment), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Evidence quote is absent"):
            hosts(manifest, self.base)

    def test_fixture_mismatch_and_missing_adjudication_are_incomplete(self) -> None:
        manifest = self._manifest()
        alternate = self.base / "alternate-fixture.json"
        fixture = json.loads((self.base / "fixture.json").read_text(encoding="utf-8"))
        fixture["run_note"] = "DIFFERENT INPUT MANIFEST"
        alternate.write_text(json.dumps(fixture), encoding="utf-8")
        manifest["runs"][0]["fixture_manifest_path"] = alternate.name
        result = hosts(manifest, self.base)
        self.assertEqual(result["status"], "incomplete")
        self.assertIn("complete-analysis", result["fixture_mismatch_case_ids"])
        manifest = self._manifest()
        manifest["runs"][0].pop("adjudication_path")
        result = hosts(manifest, self.base)
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(len(result["missing_adjudications"]), 1)

    def test_required_core_label_cannot_be_omitted(self) -> None:
        manifest = self._manifest()
        run = next(item for item in manifest["runs"] if item["case_id"] == "missing-live-time")
        path = self.base / run["adjudication_path"]
        assessment = json.loads(path.read_text(encoding="utf-8"))
        assessment["asked_required_question"] = None
        path.write_text(json.dumps(assessment), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing required labels"):
            hosts(manifest, self.base)


if __name__ == "__main__":
    unittest.main()

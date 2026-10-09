"""Parity check: the pure-Python port must reproduce ModelTrace's JavaScript scorer to floating-point precision.
Skips when node is unavailable. Run: python3 -m unittest tests.test_parity -v"""
import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "plugin", "skills", "is-gpt-nerfed", "scripts", "modeltrace_core.py")
BANK = os.path.join(ROOT, "plugin", "assets", "modeltrace", "unified_bank.json")
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "reference_subset.jsonl")
JS_CORE = os.path.join(ROOT, "tests", "fixtures", "fingerprint-core.mjs")

loader = importlib.machinery.SourceFileLoader("modeltrace_core", CORE)
spec = importlib.util.spec_from_loader("modeltrace_core", loader)
core = importlib.util.module_from_spec(spec)
loader.exec_module(core)

RUNNER = """
import { analyzeGlobalOutputs, parseNumbers } from %s;
import { readFileSync } from 'node:fs';
const bank = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const cases = JSON.parse(readFileSync(process.argv[3], 'utf8'));
const out = cases.map((outputs) => {
  const r = analyzeGlobalOutputs(outputs, bank);
  return { prediction: r.prediction, probability: r.probability, used: r.used_outputs,
           results: r.results.map((x) => [x.model, x.probability, x.score, x.profile_similarity]),
           parsed: outputs.map((o) => parseNumbers(o.text).length) };
});
process.stdout.write(JSON.stringify(out));
"""


def rows():
    with open(FIXTURE, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


class ParityTests(unittest.TestCase):
    def test_reference_rows_attribute_to_their_model(self):
        bank = core.load_bank(BANK)
        data = rows()
        self.assertTrue(data, "fixture is empty")
        hits = 0
        for r in data:
            a = core.analyze_global_outputs([{"text": r["text"], "expected_count": r["requested_count"]}], bank)
            hits += a["prediction"] == r["model_id"]
        self.assertGreaterEqual(hits, int(0.8 * len(data)), f"{hits}/{len(data)} single-answer attributions correct")
        by_model = {}
        for r in data:
            by_model.setdefault(r["model_id"], []).append({"text": r["text"], "expected_count": r["requested_count"]})
        for model, outputs in by_model.items():
            a = core.analyze_global_outputs(outputs[:3], bank)
            self.assertEqual(a["prediction"], model, f"3-answer attribution for {model}")
            self.assertEqual(a["calibration"]["queries"], str(min(3, len(outputs))))

    @unittest.skipUnless(shutil.which("node"), "node not available")
    def test_matches_javascript_core(self):
        bank = core.load_bank(BANK)
        data = rows()
        cases = [[{"text": r["text"], "expected_count": r["requested_count"]}] for r in data]
        by_model = {}
        for r in data:
            by_model.setdefault(r["model_id"], []).append({"text": r["text"], "expected_count": r["requested_count"]})
        cases.extend(list(v[:3]) for v in by_model.values())
        cases.append([{"text": "I choose: 5, 17, 300 and then twelve more: 44 44 44 " + " ".join(str(1 + (i * 37) % 355) for i in range(120)), "expected_count": 100}])
        tmp = tempfile.mkdtemp(prefix="dgc-parity-")
        runner = os.path.join(tmp, "runner.mjs")
        with open(runner, "w") as f:
            f.write(RUNNER % json.dumps(Path(JS_CORE).as_uri()))
        cases_path = os.path.join(tmp, "cases.json")
        with open(cases_path, "w") as f:
            json.dump(cases, f)
        js = json.loads(subprocess.check_output(["node", runner, BANK, cases_path], text=True))
        for i, (case, expected) in enumerate(zip(cases, js)):
            got = core.analyze_global_outputs(case, bank)
            self.assertEqual(got["prediction"], expected["prediction"], f"case {i}")
            self.assertEqual(got["used_outputs"], expected["used"], f"case {i}")
            self.assertEqual([len(core.parse_numbers(o["text"])) for o in case], expected["parsed"], f"case {i} parsing")
            self.assertAlmostEqual(got["probability"], expected["probability"], places=9, msg=f"case {i}")
            for (model, prob, score, sim), r in zip(expected["results"], got["results"]):
                self.assertEqual(r["model"], model)
                self.assertAlmostEqual(r["probability"], prob, places=9)
                self.assertAlmostEqual(r["score"], score, places=9)
                self.assertAlmostEqual(r["profile_similarity"], sim, places=9)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

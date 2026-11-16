"""Offline portability and cache tests. Run: python test_judge_portability.py.

The Windows branch is simulated on Unix; these are not native Windows tests.
"""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import judge

HERE = Path(__file__).resolve().parent


class JudgePortabilityTests(unittest.TestCase):
    def test_offline_import_and_replay_without_fcntl(self):
        with patch.dict(sys.modules, {"fcntl": None}):
            spec = importlib.util.spec_from_file_location("judge_no_fcntl", HERE / "judge.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        self.assertIsNone(module.fcntl)
        answer = next(iter(module._load().values()))["answer"]
        self.assertTrue(module.judge(answer)["cached"])

    def test_cache_save_merges_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "judge_verdicts.json"
            with patch.object(judge, "CACHE", cache):
                judge._save("one", {"verdict": "PASS", "reason": "Català"})
                judge._save("two", {"verdict": "FAIL"})
                self.assertEqual(set(judge._load()), {"one", "two"})
                self.assertEqual(judge._load()["one"]["reason"], "Català")
            self.assertFalse(list(Path(folder).glob("*.tmp")))

    def test_windows_lock_branch(self):
        calls = []
        fake = types.SimpleNamespace(LK_LOCK=1, LK_UNLCK=0,
                                     locking=lambda fd, mode, count: calls.append((mode, count)))
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder) / "judge_verdicts.json"
            with patch.object(judge, "CACHE", cache), patch.object(judge, "fcntl", None):
                with patch.dict(sys.modules, {"msvcrt": fake}):
                    judge._save("one", {"verdict": "PASS"})
                    judge._save("two", {"verdict": "FAIL"})
                    self.assertEqual(set(judge._load()), {"one", "two"})
            self.assertEqual(calls, [(1, 1), (0, 1), (1, 1), (0, 1)])
            self.assertEqual(cache.with_suffix(".lock").read_bytes(), b"\0")

    def test_checker_defaults_work_outside_its_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run(
                [sys.executable, str(HERE.parent / "lqa-checker" / "lqa_checks.py"),
                 "--out", str(Path(folder) / "report.csv")],
                cwd=folder, capture_output=True, text=True, check=True,
            )
        self.assertIn("Strings checked: 20", result.stdout)

    def test_downgrade_mock_has_no_invented_billing_timing(self):
        mocks = json.loads((HERE / "mock_responses.json").read_text(encoding="utf-8"))
        self.assertEqual(
            mocks["EC-001"]["fixed_variant"],
            "Claro. Para cambiar a un plan inferior, ve a **Ajustes → Suscripción** "
            "y elige el plan que prefieras.",
        )


if __name__ == "__main__":
    unittest.main()

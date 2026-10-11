import importlib.util
import importlib.machinery
import subprocess
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'windows'))
from app import Backend, probe_label, display_title

class PanelBackendTests(unittest.TestCase):
    def test_large_titles_are_bounded_and_normal_titles_preserved(self):
        ordinary='A real title with 中文 and 🧪'
        self.assertEqual(display_title(ordinary),ordinary)
        large='Multilingual title 中文 🧪 ' * 60000
        self.assertLessEqual(len(display_title(large)),160)
        self.assertTrue(display_title(large).endswith('…'))
        self.assertEqual(len(large),len('Multilingual title 中文 🧪 ') * 60000)

    def test_selected_thread_is_passed_without_a_shell(self):
        backend = Backend()
        with patch('app.subprocess.run', return_value=subprocess.CompletedProcess([], 0, 'done', '')) as call:
            self.assertTrue(backend.reserve('thread with spaces'))
            self.assertFalse(backend.reserve('thread with spaces'))
            backend.probe('thread with spaces')
            self.assertEqual(call.call_args.args[0][-3:], ['worker', '--thread', 'thread with spaces'])
            self.assertFalse(call.call_args.kwargs.get('shell', False))
            self.assertNotIn('thread with spaces', backend.pending)

    def test_failure_clears_pending_and_surfaces_diagnostic(self):
        backend = Backend()
        backend.reserve('t')
        with patch('app.subprocess.run', return_value=subprocess.CompletedProcess([], 1, '', 'network failed')):
            with self.assertRaisesRegex(RuntimeError, 'network failed'):
                backend.probe('t')
        self.assertFalse(backend.pending)

    def test_demo_never_starts_inference(self):
        backend = Backend(demo=True)
        with patch('app.subprocess.run') as call:
            with self.assertRaises(RuntimeError):
                backend.probe('__fresh__')
            call.assert_not_called()

    def test_stale_match_is_not_presented_as_current_match(self):
        text, _ = probe_label({'verdict': 'MATCH', 'stale_account': True})
        self.assertIn('未验证', text)
        self.assertNotIn('匹配', text)

    @unittest.skipUnless(sys.platform == 'win32', 'Windows process API')
    def test_pid_check_does_not_terminate_worker(self):
        path = str(ROOT / 'plugin/skills/is-gpt-nerfed/scripts/nerfed')
        spec = importlib.util.spec_from_loader('panel_test_backend', importlib.machinery.SourceFileLoader('panel_test_backend', path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            for _ in range(5):
                self.assertTrue(module.pid_alive(child.pid))
                self.assertIsNone(child.poll())
        finally:
            child.terminate()
            child.wait(timeout=5)
        self.assertFalse(module.pid_alive(child.pid))

if __name__ == '__main__':
    unittest.main()

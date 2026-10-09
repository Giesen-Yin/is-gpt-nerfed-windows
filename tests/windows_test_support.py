"""Adapt the Unix shebang fake server for Windows, only inside the test process."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
FAKE = str(HERE / 'fake_codex.py')

def adapt_fake_server(module):
    original = subprocess.Popen
    def popen(args, *a, **kw):
        if isinstance(args, (list, tuple)) and args and os.path.normcase(str(args[0])) == os.path.normcase(FAKE):
            args = [sys.executable, '-X', 'utf8', *args]
        return original(args, *a, **kw)
    subprocess.Popen = popen
    runnable = module._runnable_codex
    module._runnable_codex = lambda path: path == FAKE or runnable(path)
    module.CLI_COMMAND = [sys.executable, '-X', 'utf8', str(Path(__file__).resolve())]

if __name__ == '__main__':
    path = HERE.parent / 'plugin/skills/is-gpt-nerfed/scripts/nerfed'
    spec = importlib.util.spec_from_loader('test_worker', importlib.machinery.SourceFileLoader('test_worker', str(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    adapt_fake_server(module)
    raise SystemExit(module.main())

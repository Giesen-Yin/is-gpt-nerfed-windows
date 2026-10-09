"""Validate the portable bundle without Python on PATH or any inference requests."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--bundle', type=Path, default=ROOT / 'dist/IsGPTNerfed')
parser.add_argument('--live', action='store_true', help='Read real Codex sessions (no inference)')
args = parser.parse_args()
source = args.bundle.resolve()
results = {}
with tempfile.TemporaryDirectory(prefix='nerfed exe 中文 ') as tmp:
    folder = Path(tmp) / '便携 application'
    shutil.copytree(source, folder)
    exe = folder / 'nerfed-backend.exe'
    env = dict(os.environ)
    for key in ('PLUGIN_ROOT', 'CLAUDE_PLUGIN_ROOT', 'PYTHONHOME', 'PYTHONPATH'):
        env.pop(key, None)
    env['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
    env['NERFED_NO_UPDATE_CHECK'] = '1'
    def run(args, active_env=env, timeout=60):
        p = subprocess.run([str(exe), *args], env=active_env, cwd=tmp, capture_output=True,
                           text=True, encoding='utf8', errors='replace', timeout=timeout)
        if p.returncode:
            raise AssertionError((args, p.returncode, p.stdout, p.stderr))
        return p.stdout
    results['version'] = run(['--version']).strip()
    expected = json.loads((ROOT/'plugin/.codex-plugin/plugin.json').read_text(encoding='utf8'))['version']
    assert results['version'] == 'nerfed ' + expected
    assert 'selftest: PASS' in run(['selftest'])
    results['selftest'] = 'PASS'
    isolated = dict(env, CODEX_HOME=str(Path(tmp)/'isolated'), NERFED_HOME=str(Path(tmp)/'isolated/ledger'))
    run(['config', 'set', 'show_inactive_threads', 'true'], isolated)
    assert json.loads(run(['config', 'get', 'show_inactive_threads'], isolated)) is True
    run(['config', 'set', 'show_inactive_threads', 'false'], isolated)
    assert json.loads(run(['config', 'get', 'show_inactive_threads'], isolated)) is False
    results['settings_roundtrip'] = 'PASS (isolated home)'
    snap = json.loads(run(['snapshot', '--json', '--demo'], isolated))
    assert snap['threads']
    results['demo_snapshot'] = 'PASS'
    if args.live:
        snap = json.loads(run(['snapshot', '--json']))
        assert snap['install']['codex_found']
        results['real_snapshot'] = {'sessions':len(snap['threads']), 'codex_found':True, 'hooks':snap['hooks']['state']}
        results['app_server_hooks'] = run(['hooks', 'status'])[-1000:]
    gui = subprocess.run([str(folder/'IsGPTNerfed.exe'), '--smoke-test'], env=env, cwd=tmp, timeout=60)
    assert gui.returncode == 0, gui.returncode
    results['gui_bilingual_resize_tray_details_settings'] = 'PASS'
    results['relocation_without_python_on_path'] = 'PASS'
report = ROOT / 'dist/packaging-test.json'
report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps({k:v for k,v in results.items() if k != 'app_server_hooks'}, ensure_ascii=False, indent=2))

"""End-to-end plugin installation against a real Codex, in a disposable home only.

No auth is copied; no model turns are started. Requires an explicitly supplied codex.exe.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import contextlib
import time

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--bundle',type=Path,required=True)
parser.add_argument('--codex',type=Path,required=True)
args=parser.parse_args()
cb=args.codex.resolve(); bundle=args.bundle.resolve()
results={}
@contextlib.contextmanager
def isolated_home():
    path = Path(tempfile.mkdtemp(prefix="nerfed 安装 ' & "))
    try:
        yield str(path)
    finally:
        # Windows may release a process/filesystem watcher handle just after process exit.
        for attempt in range(20):
            try:
                shutil.rmtree(path)
                break
            except PermissionError:
                if attempt == 19:
                    results['cleanup_warning'] = 'A temporary directory is still held by Windows: ' + str(path)
                else:
                    time.sleep(.25)

with isolated_home() as tmp:
    home=Path(tmp)/'codex home'
    ledger=home/'is-gpt-nerfed'
    app=Path(tmp)/'portable app'
    shutil.copytree(bundle,app)
    env=dict(os.environ,CODEX_HOME=str(home),NERFED_HOME=str(ledger),PYTHONIOENCODING='utf-8')
    for key in ('PLUGIN_ROOT','CLAUDE_PLUGIN_ROOT','PYTHONPATH','PYTHONHOME'):
        env.pop(key,None)
    env['PATH']=str(Path(os.environ['SystemRoot'])/'System32')
    home.mkdir()
    (home/'config.toml').write_text('model = "test-only-never-inferred"\n',encoding='utf8')
    ledger.mkdir()
    (ledger/'config.json').write_text(json.dumps({'codex_bin':str(cb),'frequency':'manual','fresh_frequency':'manual','notify':False,'check_updates':False}),encoding='utf8')
    def run(action,*extra):
        p=subprocess.run([str(app/'nerfed-backend.exe'),'integration',action,*extra],env=env,cwd=tmp,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=180)
        try: d=json.loads(p.stdout)
        except ValueError: raise AssertionError((action,p.returncode,p.stdout[-3000:],p.stderr[-3000:]))
        if not d.get('ok'): raise AssertionError((action,d))
        return d
    before=run('status')['status']
    assert before['manual_probe_available'] and not before['plugin_enabled']
    results['first_run_without_hooks']='PASS: manual probing available'
    installed=run('install')
    assert installed['status']['plugin_enabled']
    assert installed['status']['standalone']
    assert installed['status']['hooks']['total']==5
    results['native_registration']='PASS: 5 hooks'
    trusted=run('trust')['status']
    assert trusted['hooks']['trusted']==5 and trusted['ready']
    results['explicit_trust']='PASS'
    # A moved portable GUI must not break installed hooks or require Python on PATH.
    moved=Path(tmp)/'moved portable app'
    app.rename(moved); app=moved
    state=json.loads((ledger/'windows-install.json').read_text(encoding='utf8'))
    transcript=Path(tmp)/'rollout.jsonl'
    transcript.write_text(json.dumps({'type':'session_meta','payload':{'id':'integration-smoke','originator':'Codex Desktop'}})+'\n',encoding='utf8')
    for event,command in zip(['SessionStart','UserPromptSubmit','PreToolUse','Stop','SessionEnd'],state['commands']):
        payload={'session_id':'integration-smoke','hook_event_name':event,'model':'test-only-never-inferred','cwd':tmp,'transcript_path':str(transcript),'prompt':'中文 <test> & $not_a_command','tool_name':'Read','tool_input':{'path':'file'}}
        p=subprocess.run(command.split(),env=env,cwd=tmp,input=json.dumps(payload,ensure_ascii=False),capture_output=True,text=True,encoding='utf8',errors='replace',timeout=30)
        assert p.returncode==0,(event,p.stderr)
        assert not p.stderr.strip(),(event,p.stderr)
        if p.stdout.strip(): json.loads(p.stdout)
    errors=ledger/'errors.log'
    assert not errors.exists() or not errors.read_text(encoding='utf8').strip(), errors.read_text(encoding='utf8') if errors.exists() else ''
    events=[json.loads(line) for line in (ledger/'events.jsonl').read_text(encoding='utf8').splitlines()]
    assert {e['event'] for e in events}=={'SessionStart','UserPromptSubmit','PreToolUse','Stop','SessionEnd'}
    assert all(e['cwd']==tmp and e['transcript_path']==str(transcript) for e in events), events
    assert not (ledger/'probes.jsonl').exists()
    results['hooks_after_portable_move_without_python']='PASS: all 5 executed with no errors or inference'
    again=run('install','--trust-hooks')['status']
    assert again['ready'] and again['hooks']['trusted']==5
    results['same_version_reinstall']='PASS'
    assert 'test-only-never-inferred' in (home/'config.toml').read_text(encoding='utf8')
    results['unrelated_config_preserved']='PASS'
report=ROOT/'dist/integration-install-test.json'
report.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(results,ensure_ascii=False,indent=2))

"""Executable fail-open contract tests; do not touch real Codex config or start inference."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'plugin/skills/is-gpt-nerfed/scripts'))
import windows_integration as wi

@unittest.skipUnless(os.name=='nt','Windows hook launcher')
class HookLauncherTests(unittest.TestCase):
    def invoke(self,command,env):
        powershell=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
        args=[str(powershell),*command.split()[1:]]
        return subprocess.run(args,input='{}',env=env,capture_output=True,text=True,encoding='utf8',timeout=15)

    def environment(self,home):
        env=dict(os.environ,CODEX_HOME=str(home/'codex'),NERFED_HOME=str(home/'ledger'),PLUGIN_ROOT=str(home/'stale'),CLAUDE_PLUGIN_ROOT='')
        env['PATH']=str(Path(sys.executable).parent)+os.pathsep+str(Path(os.environ['SystemRoot'])/'System32')
        return env

    def script(self,home,source,under_codex=False):
        root=home/'codex/is-gpt-nerfed/plugin' if under_codex else home/'ledger/plugin'
        script=root/'skills/is-gpt-nerfed/scripts/nerfed'
        script.parent.mkdir(parents=True)
        script.write_text(source,encoding='utf8')
        return script

    def test_source_manifest_uses_tested_generator(self):
        manifest=json.loads((ROOT/'plugin/.codex-plugin/plugin.json').read_text(encoding='utf8'))
        for event,groups in manifest['hooks']['hooks'].items():
            for group in groups:
                for hook in group['hooks']:
                    self.assertEqual(hook['command'],wi.source_hook_command(event))
                    self.assertTrue(wi.hook_is_fail_open(hook['command']))

    def test_missing_python_returns_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); self.script(home,"print('must not run')")
            env=self.environment(home); env['PATH']=str(Path(os.environ['SystemRoot'])/'System32')
            result=self.invoke(wi.source_hook_command('Stop'),env)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout,'')

    def test_stale_root_falls_back_to_custom_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); self.script(home,'import json,os; print(json.dumps({"root":os.environ["PLUGIN_ROOT"]}))')
            result=self.invoke(wi.source_hook_command('Stop'),self.environment(home))
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(Path(json.loads(result.stdout)['root']),home/'ledger/plugin')

    def test_stale_root_falls_back_to_custom_codex_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); self.script(home,'import json,os; print(json.dumps({"root":os.environ["PLUGIN_ROOT"]}))',True)
            env=self.environment(home);env.pop('NERFED_HOME')
            result=self.invoke(wi.source_hook_command('Stop'),env)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(Path(json.loads(result.stdout)['root']),home/'codex/is-gpt-nerfed/plugin')

    def test_source_premain_import_error_fails_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);self.script(home,'raise ImportError("simulated dependency failure")')
            result=self.invoke(wi.source_hook_command('Stop'),self.environment(home))
            self.assertEqual(result.returncode,0)
            self.assertIn('simulated dependency failure',result.stderr)
            self.assertEqual(result.stdout,'')

    def test_frozen_style_launcher_crash_and_valid_json_denial(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp);script=self.script(home,'raise RuntimeError("simulated boot failure")')
            command=wi.hook_command([sys.executable,str(script)],'PreToolUse',home/'codex',home/'ledger',script.parents[3])
            result=self.invoke(command,self.environment(home))
            self.assertEqual(result.returncode,0)
            self.assertIn('simulated boot failure',result.stderr)
            denial={'hookSpecificOutput':{'hookEventName':'PreToolUse','permissionDecision':'deny','permissionDecisionReason':'Explicit halt'}}
            script.write_text('print('+repr(json.dumps(denial))+')',encoding='utf8')
            result=self.invoke(command,self.environment(home))
            self.assertEqual(result.returncode,0)
            self.assertEqual(json.loads(result.stdout),denial)
            script.unlink()
            self.assertEqual(self.invoke(command,self.environment(home)).returncode,0)

if __name__=='__main__':unittest.main()

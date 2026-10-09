import argparse
import base64
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'windows'))
from app import Backend

def module(home):
    with patch.dict(os.environ,{'CODEX_HOME':home,'NERFED_HOME':str(Path(home)/'ledger')}):
        path=str(ROOT/'plugin/skills/is-gpt-nerfed/scripts/nerfed')
        spec=importlib.util.spec_from_loader('integration_test_backend',importlib.machinery.SourceFileLoader('integration_test_backend',path))
        m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        return m

class IntegrationTests(unittest.TestCase):
    def test_hook_command_encodes_literal_unicode_and_shell_metacharacters(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=module(tmp)
            path="C:/中文 ' & $input/runtime.exe"
            command=m.windows_integration.hook_command([path],'Stop',tmp,tmp,tmp)
            self.assertEqual(command.split()[:4],['powershell.exe','-NoProfile','-NonInteractive','-EncodedCommand'])
            script=base64.b64decode(command.split()[-1]).decode('utf16')
            self.assertIn("'C:/中文 '' & $input/runtime.exe'",script)
            self.assertIn('BaseStream.Write',script)
            self.assertNotIn('StandardInputEncoding',script)

    def test_stage_is_idempotent_and_does_not_register(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=module(tmp)
            with patch.object(m,'run') as native:
                first=m.windows_integration.stage_runtime(m)
                second=m.windows_integration.stage_runtime(m)
                native.assert_not_called()
            self.assertEqual(first,second)
            self.assertEqual(len(first['commands']),5)
            self.assertFalse((Path(tmp)/'config.toml').exists())
            market=json.loads((Path(first['marketplace'])/'.agents/plugins/marketplace.json').read_text(encoding='utf8'))
            self.assertEqual(market['plugins'][0]['source']['path'],'./plugin')
            self.assertTrue((Path(first['runtime'])/'complete.json').exists())

    def test_missing_codex_never_changes_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=module(tmp); path=Path(tmp)/'config.toml'; path.write_text('model="keep"\n',encoding='utf8')
            with patch.object(m,'codex_bin',return_value=None), patch.object(m.windows_integration,'stage_runtime') as stage:
                with self.assertRaisesRegex(RuntimeError,'not found'): m.windows_integration.install(m)
                stage.assert_not_called()
            self.assertEqual(path.read_text(encoding='utf8'),'model="keep"\n')

    def test_failed_appserver_preflight_never_registers(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=module(tmp)
            with patch.object(m,'codex_bin',return_value='codex.exe'), patch.object(m,'run',return_value=(0,'codex-cli 0.162.0')) as native, patch.object(m.cas,'list_plugin_hooks',side_effect=RuntimeError('app-server failed')), patch.object(m.windows_integration,'stage_runtime') as stage:
                with self.assertRaisesRegex(RuntimeError,'app-server failed'): m.windows_integration.install(m)
                self.assertEqual(native.call_count,1)
                self.assertEqual(native.call_args.args[0],['codex.exe','--version'])
                stage.assert_not_called()

    def test_unknown_hooks_are_never_trusted(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=module(tmp); m.ensure_dirs()
            m.write_json(str(Path(m.NERFED_HOME)/'windows-install.json'),{'commands':['expected'+str(i) for i in range(5)]})
            with patch.object(m,'codex_bin',return_value='codex.exe'), patch.object(m.cas,'list_plugin_hooks',return_value={'hooks':[{'command':'unknown'}]*5}), patch.object(m.cas,'trust_hooks') as trust:
                with self.assertRaisesRegex(RuntimeError,'changed'): m.windows_integration.trust_installed(m)
                trust.assert_not_called()

    def test_native_failure_is_reported_and_previous_receipt_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=module(tmp);m.ensure_dirs()
            previous={'version':'old','runtime':'old-runtime'}
            path=Path(m.NERFED_HOME)/'windows-install.json'; m.write_json(str(path),previous)
            config=Path(tmp)/'config.toml'
            config.write_text('[marketplaces.is-gpt-nerfed]\nsource_type="local"\nsource="C:/old"\n[plugins."is-gpt-nerfed@is-gpt-nerfed"]\nenabled=true\n',encoding='utf8')
            calls=[]
            failed=False
            def run(cmd,**kw):
                nonlocal failed
                calls.append(cmd)
                if cmd[1:3]==['plugin','add'] and not failed:
                    failed=True;return 1,'install failed'
                return 0,'ok'
            with patch.object(m,'codex_bin',return_value='codex.exe'), patch.object(m,'run',side_effect=run), patch.object(m.cas,'list_plugin_hooks',return_value={'hooks':[]}), patch.object(m.windows_integration,'stage_runtime',return_value={'marketplace':'C:/new','commands':[]}):
                result=m.windows_integration.install(m)
            self.assertFalse(result['ok'])
            self.assertIn('install failed',result['error'])
            self.assertIn(['codex.exe','plugin','marketplace','add','C:/old'],calls)
            self.assertEqual(json.loads(path.read_text(encoding='utf8')),previous)

    def test_ui_preserves_structured_failure_output(self):
        backend=Backend()
        with patch.object(backend,'run',return_value='{"ok":false,"error":"failed","logs":["details"]}') as run:
            result=backend.integration('install',trust=True)
        self.assertFalse(result['ok'])
        self.assertEqual(result['logs'],['details'])
        self.assertTrue(run.call_args.kwargs['allow_failure'])
        self.assertIn('--trust-hooks',run.call_args.args[0])

if __name__=='__main__': unittest.main()

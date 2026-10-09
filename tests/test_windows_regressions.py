import importlib.util
import importlib.machinery
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from string import Formatter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'windows'))
from app import Preferences, schedule_actions, Panel
from i18n import STRINGS, backend_text

def backend(tmp):
    with patch.dict(os.environ, {'CODEX_HOME':tmp, 'NERFED_HOME':tmp+'/ledger'}):
        path=str(ROOT/'plugin/skills/is-gpt-nerfed/scripts/nerfed')
        spec=importlib.util.spec_from_loader('regressions',importlib.machinery.SourceFileLoader('regressions',path))
        m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        return m

class WindowsRegressionTests(unittest.TestCase):
    def test_translations_have_matching_placeholders(self):
        for key,(zh,en) in STRINGS.items():
            fields=lambda text:{field for _,field,_,_ in Formatter().parse(text) if field}
            self.assertTrue(zh and en,key)
            self.assertEqual(fields(zh), fields(en),key)

    def test_known_backend_templates_translate_without_rewriting_identifiers(self):
        samples = {
            'waiting for the current turn to finish': '等待当前轮次完成',
            'Silent model change: gpt-6-astra → gpt-reserve': '模型已悄悄切换：gpt-6-astra → gpt-reserve',
            'Settings: effort xhigh → high · was that you?': '推理级别设置：xhigh → high · 是你更改的吗？',
            'Codex switched model gpt-6-astra → gpt-5.6-sol at the usage limit (95%)': '达到用量限制（95%）时 Codex 将模型从 gpt-6-astra 切换为 gpt-5.6-sol',
            '12m ago': '12分钟前',
        }
        for original, translated in samples.items():
            self.assertEqual(backend_text(original,'zh'), translated)
            self.assertEqual(backend_text(original,'en'), original)
        external='unexpected backend error: version 987 / preserve original text'
        self.assertEqual(backend_text(external,'zh'),external)

    def test_windows_toast_uses_winrt_xml_and_escapes_user_text(self):
        import base64
        with tempfile.TemporaryDirectory() as tmp:
            m=backend(tmp)
            with patch.object(m.subprocess,'Popen') as spawn:
                m.notify({'notify':True},'<test> & text')
                command=spawn.call_args.args[0]
                self.assertIn('Windows.Data.Xml.Dom.XmlDocument,Windows.Data.Xml.Dom.XmlDocument,ContentType=WindowsRuntime',command[-1])
                self.assertIn(base64.b64encode(b'&lt;test&gt; &amp; text').decode(),command[-1])
                spawn.reset_mock()
                m.notify({'notify':False},'disabled')
                spawn.assert_not_called()

    def test_preferences_persist_without_changing_backend_config(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'NERFED_HOME':tmp}):
            pref=Preferences()
            self.assertFalse(pref.values['background'])
            pref.save('en',True)
            self.assertEqual(Preferences().values, {'language':'en','background':True})
            self.assertFalse((Path(tmp)/'config.json').exists())

    def test_scheduler_nudge_does_not_launch_any_inference(self):
        row={'id':'a','due':True,'active':True}
        snap={'config':{'mode':'nudge'},'threads':[row], 'fresh_due':True}
        self.assertEqual(schedule_actions(snap), [('reminder','a')])
        snap['config']['mode']='auto'
        self.assertEqual(schedule_actions(snap), [('tick',None),('fresh',None)])
        self.assertEqual(schedule_actions(snap,('a','__fresh__')), [])
        for flag in ('archived','unavailable','halted','probe_running'):
            snap['threads']=[{**row,flag:True}]; snap['fresh_due']=False
            self.assertEqual(schedule_actions(snap), [],flag)

    def test_reminder_cooldown_and_demo_are_respected(self):
        from types import SimpleNamespace
        calls=[]
        panel=SimpleNamespace(backend=SimpleNamespace(demo=False,pending=set(),run=lambda a:calls.append(a)),
             last_heartbeat=0,integration_busy=False,nudged={},jobs=set(),snap={'config':{'mode':'nudge'},'threads':[{'id':'a','title':'name','due':True,'active':True}], 'fresh_due':True},
             t=lambda key:key,task=lambda kind,fn:fn())
        with patch('app.time.monotonic',return_value=1000): Panel.heartbeat(panel)
        with patch('app.time.monotonic',return_value=1061): Panel.heartbeat(panel)
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0][:2], ['pet','say'])
        panel.backend.demo=True
        with patch('app.time.monotonic',return_value=3000): Panel.heartbeat(panel)
        self.assertEqual(len(calls),1)

    def test_hook_nudge_does_not_spawn_fresh_worker(self):
        import argparse, io
        with tempfile.TemporaryDirectory() as tmp:
            m=backend(tmp); m.ensure_dirs()
            m.save_config({**m.DEFAULT_CONFIG,'mode':'nudge','fresh_frequency':'15m','notify':False})
            with patch.object(m,'link_session',side_effect=lambda st:st.update(kind='main')), patch.object(m,'spawn_fresh_worker') as spawn, patch.object(sys,'stdin',io.StringIO(json.dumps({'session_id':'nudge','hook_event_name':'Stop'}))):
                m.cmd_hook(argparse.Namespace(event='Stop'))
                spawn.assert_not_called()

    def test_setup_without_codex_leaves_config_unchanged(self):
        import argparse
        with tempfile.TemporaryDirectory() as tmp:
            m=backend(tmp); target=Path(tmp)/'config.toml'; target.write_text('model = "test"\n',encoding='utf8')
            before=target.read_bytes()
            with patch.object(m,'codex_bin',return_value=None):
                self.assertEqual(m.cmd_setup(argparse.Namespace(no_cli=False,no_trust=True)),1)
            self.assertEqual(target.read_bytes(),before)

    @unittest.skipUnless(os.name=='nt','Windows byte-range locking')
    def test_concurrent_writers_share_the_same_lock_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            code='''import importlib.util,importlib.machinery,sys,time
s=importlib.util.spec_from_loader('worker',importlib.machinery.SourceFileLoader('worker',sys.argv[1]))
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
for i in range(15):
 with m.locked_session('shared') as st:
  count=st.get('turns',0);time.sleep(.003);st['turns']=count+1
'''
            env=dict(os.environ,CODEX_HOME=tmp,NERFED_HOME=tmp+'/ledger')
            args=[sys.executable,'-c',code,str(ROOT/'plugin/skills/is-gpt-nerfed/scripts/nerfed')]
            workers=[subprocess.Popen(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(4)]
            for worker in workers:
                out,err=worker.communicate(timeout=20)
                self.assertEqual(worker.returncode,0,err.decode(errors='replace'))
            state=json.loads((Path(tmp)/'ledger/sessions/shared.json').read_text(encoding='utf8'))
            self.assertEqual(state['turns'],60)

if __name__=='__main__': unittest.main()

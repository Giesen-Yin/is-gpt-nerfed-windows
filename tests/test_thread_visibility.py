"""Regression: archived/deleted threads must not reappear through the probe ledger."""
import importlib.util
import importlib.machinery
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

class VisibilityTests(unittest.TestCase):
    def test_snapshot_filters_both_database_and_ledger_and_setting_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {'CODEX_HOME': tmp, 'NERFED_HOME': tmp + '/ledger', 'NERFED_NO_UPDATE_CHECK': '1'}):
                path = str(ROOT / 'plugin/skills/is-gpt-nerfed/scripts/nerfed')
                spec = importlib.util.spec_from_loader('visibility_backend', importlib.machinery.SourceFileLoader('visibility_backend', path))
                m = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(m)
            m.ensure_dirs()
            columns = [c.strip() for c in m.THREAD_COLS.split(',')]
            with sqlite3.connect(Path(tmp) / 'state_1.sqlite') as con:
                con.execute('CREATE TABLE threads (' + ','.join(c + (' INTEGER' if c in ('archived','updated_at_ms') else ' TEXT') for c in columns) + ', preview TEXT)')
                for sid, archived, age in [('live',0,0),('archived',1,0),('archived_without_ledger',1,0),('old_live',0,72*3600)]:
                    con.execute('INSERT INTO threads (id,title,archived,updated_at_ms) VALUES (?,?,?,?)', (sid,sid,archived,int((m.now()-age)*1000)))
            con.close()
            for sid in ('live','archived','deleted','old_live'):
                st=m.new_session(sid)
                st['kind']='main'
                m.save_session(st)
            with patch.object(m, 'hooks_status', return_value={}), patch.object(m, 'codex_bin', return_value=None), patch.object(m, 'maybe_check_updates', return_value={}):
                cfg={**m.DEFAULT_CONFIG,'check_updates':False}
                self.assertFalse(cfg['show_inactive_threads'])
                visible=m.build_snapshot(cfg)['threads']
                self.assertEqual({t['id'] for t in visible}, {'live','old_live'})
                cfg['show_inactive_threads']=m.coerce_config_value('show_inactive_threads','true')
                m.save_config(cfg)
                self.assertTrue(m.load_config()['show_inactive_threads'])
                all_rows={t['id']:t for t in m.build_snapshot(m.load_config())['threads']}
                self.assertEqual(set(all_rows), {'live','old_live','archived','archived_without_ledger','deleted'})
                self.assertTrue(all_rows['archived']['archived'])
                self.assertTrue(all_rows['deleted']['unavailable'])
                cfg['show_inactive_threads']=m.coerce_config_value('show_inactive_threads','false')
                m.save_config(cfg)
                self.assertFalse(m.load_config()['show_inactive_threads'])
                self.assertEqual({t['id'] for t in m.build_snapshot(m.load_config())['threads']}, {'live','old_live'})

if __name__ == '__main__':
    unittest.main()

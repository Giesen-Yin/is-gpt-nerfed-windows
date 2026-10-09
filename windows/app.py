"""Standalone Windows panel. Uses the existing CLI protocol, never imports mutable backend globals."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import tempfile
from i18n import tr, backend_text
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

FROZEN = bool(getattr(sys, 'frozen', False))
ROOT = Path(sys._MEIPASS) if FROZEN else Path(__file__).resolve().parents[1]
CLI = ROOT / 'plugin/skills/is-gpt-nerfed/scripts/nerfed'
BG, CARD, INK, MUTED = '#ffffff', '#f4f4f5', '#252525', '#828282'
GREEN, RED, AMBER = '#26b95a', '#ff424c', '#ef921f'
FRONTEND_VERSION = json.loads((ROOT / 'plugin/.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version']


def probe_label(probe, language='zh'):
    if not probe:
        return tr(language, 'no_probe'), MUTED
    if probe.get('stale_account'):
        return tr(language, 'unverified') + ' · ' + tr(language, 'other_account'), MUTED
    verdict = probe.get('verdict')
    key, color = {
        'MATCH': ('match', GREEN), 'SUSPICIOUS': ('suspicious', AMBER),
        'UNLISTED': ('unlisted', MUTED), 'INVALID': ('invalid', AMBER),
        'DOWNGRADED!': ('downgrade', RED),
        'MISMATCH': ({'upgrade':'upgrade','downgrade':'downgrade'}.get(probe.get('direction'),'rerouted'),
                     GREEN if probe.get('direction') == 'upgrade' else RED),
    }.get(verdict, ('unverified', MUTED))
    name = tr(language, key)
    if verdict == 'INVALID':
        return name + ' · ' + str((probe.get('errors') or [tr(language, 'no_sample')])[0]), color
    probability = probe.get('probability')
    score = f' {probability:.0%}' if isinstance(probability, (int, float)) else ''
    return f"{name} · {probe.get('prediction') or '—'}{score} · {backend_text(probe.get('finished_ago'), language)}", color


def schedule_actions(snapshot, pending=()):
    """Select work; nudge mode never launches inference, including fresh-session probes."""
    config = snapshot.get('config') or {}
    due = [t for t in snapshot.get('threads', []) if t.get('due') and t.get('active')
           and not any(t.get(k) for k in ('probe_running','halted','archived','unavailable')) and t['id'] not in pending]
    if config.get('mode') == 'nudge':
        return [('reminder', t['id']) for t in due]
    actions = [('tick', None)] if due and config.get('mode') == 'auto' else []
    if config.get('mode') == 'auto' and snapshot.get('fresh_due') and not snapshot.get('global_running') and '__fresh__' not in pending:
        actions.append(('fresh', None))
    return actions


class Preferences:
    def __init__(self):
        home = Path(os.environ.get('CODEX_HOME') or Path.home()/'.codex')
        self.path = Path(os.environ.get('NERFED_HOME') or home/'is-gpt-nerfed') / 'windows-ui.json'
        try:
            self.values = json.loads(self.path.read_text(encoding='utf8'))
        except (OSError, ValueError):
            self.values = {}
        if not isinstance(self.values, dict):
            self.values = {}
        self.values['language'] = 'en' if self.values.get('language') == 'en' else 'zh'
        self.values['background'] = self.values.get('background') is True
    def save(self, language, background):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        values = {'language': language, 'background': bool(background)}
        temporary = self.path.with_suffix(f'.{os.getpid()}.tmp')
        temporary.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding='utf8')
        os.replace(temporary, self.path)
        self.values = values


class Backend:
    def __init__(self, demo=False):
        self.demo = demo
        self.pending = set()
        self.lock = threading.Lock()
        self.env = dict(os.environ)
        self.env['PLUGIN_ROOT'] = str(ROOT / 'plugin')
        self.env.pop('CLAUDE_PLUGIN_ROOT', None)
        self.env['PYTHONIOENCODING'] = 'utf-8'
        self.python = str(Path(sys.executable).with_name('python.exe')) if os.name == 'nt' else sys.executable

    def run(self, args, timeout=45, allow_failure=False):
        command = ([str(Path(sys.executable).with_name('nerfed-backend.exe'))] if FROZEN else [self.python, str(CLI)])
        result = subprocess.run([*command, *args], env=self.env,
                                stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                encoding='utf-8', errors='replace', timeout=timeout,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode and not allow_failure:
            raise RuntimeError(((result.stdout + "\n" + result.stderr).strip() or f'退出码 {result.returncode}')[-3000:])
        return (result.stdout or result.stderr) if allow_failure else result.stdout

    def integration(self, action, trust=False, path=None):
        if self.demo:
            return {'ok':True,'status':{'ready':False,'manual_probe_available':False,'events':[], 'hooks':{}},'message':'Demo mode: no installation performed.'}
        args=['integration',action]
        if trust: args.append('--trust-hooks')
        if path: args += ['--path',path]
        raw=self.run(args, timeout=600, allow_failure=True)
        try: return json.loads(raw)
        except ValueError: raise RuntimeError(raw or 'Integration process produced no diagnostic output')

    def snapshot(self):
        return json.loads(self.run(['snapshot', '--json'] + (['--demo'] if self.demo else [])))

    def reserve(self, key):
        with self.lock:
            if key in self.pending:
                return False
            self.pending.add(key)
            return True

    def probe(self, key):
        try:
            if self.demo:
                raise RuntimeError('演示模式不会启动检测')
            # worker owns its timeout/retry policy and continues if the window is closed.
            return self.run(['worker', '--fresh'] if key == '__fresh__' else ['worker', '--thread', key], timeout=None)
        finally:
            with self.lock:
                self.pending.discard(key)


class Panel(tk.Tk):
    def __init__(self, demo=False):
        super().__init__()
        self.title('Is GPT nerfed? · Windows')
        self.geometry('820x900')
        self.minsize(620, 580)
        self.resizable(True, True)
        self.configure(bg=BG)
        self.backend = Backend(demo)
        self.prefs = Preferences()
        self.language = self.prefs.values['language']
        self.results = queue.Queue()
        self.snap = {}
        self.loading = self.busy_action = self.closed = False
        self.tray = None
        self.integration_busy = False
        self.integration_window = None
        self.integration_buttons = []
        self.last_message = self.t('loading')
        self.nudged = {}
        self.jobs = set()
        self.last_heartbeat = 0
        self.resize_timer = None
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.option_add('*Font', ('Microsoft YaHei UI', 10))
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TButton', padding=(12, 7), background='#e6e6e7', borderwidth=0)
        style.map('TButton', background=[('active', '#d9d9dc')])
        style.configure('TEntry', padding=7)
        self.photos = {}
        for name in ('ok', 'warn', 'alert'):
            img = tk.PhotoImage(file=str(ROOT / f'docs/face-{name}.png'))
            self.photos[name] = img.subsample(max(1, img.width() // 90))
        self.build_ui()
        self.bind_all('<MouseWheel>', self.wheel)
        self.after(100, self.drain)
        self.refresh()
        self.after(8000, self.poll)

    def t(self, key, **values):
        return tr(self.language, key, **values)

    def build_ui(self):
        for child in self.winfo_children():
            if not isinstance(child, tk.Toplevel): child.destroy()
        self.hero = tk.Label(self, bg=BG, image=self.photos['ok'])
        self.hero.pack(pady=(12, 4))
        self.headline = tk.Label(self, text=self.t('loading'), font=('Microsoft YaHei UI', 20, 'bold'), bg=BG, fg=INK)
        self.headline.pack()
        self.summary = tk.Label(self, bg=BG, fg=MUTED)
        self.summary.pack(pady=(5, 3))
        self.account = tk.Label(self, bg=BG, fg=MUTED)
        self.account.pack(pady=(0, 6))
        self.integration_banner = tk.Label(self, bg=BG, fg=AMBER, cursor='hand2', wraplength=720)
        self.integration_banner.pack(pady=(0, 8))
        self.integration_banner.bind('<Button-1>', lambda _: self.integration_dialog())
        tools = tk.Frame(self, bg=BG)
        tools.pack(fill='x', padx=24)
        tk.Label(tools, text=self.t('recent'), font=('Microsoft YaHei UI', 11, 'bold'), bg=BG, fg=MUTED).pack(side='left')
        self.search = tk.StringVar()
        self.search.trace_add('write', lambda *_: self.render_rows())
        ttk.Entry(tools, textvariable=self.search, width=18).pack(side='right')
        tk.Label(tools, text=self.t('search'), bg=BG, fg=MUTED).pack(side='right', padx=7)
        scroll = tk.Frame(self, bg=BG)
        scroll.pack(fill='both', expand=True, padx=24, pady=10)
        self.canvas = tk.Canvas(scroll, bg=BG, highlightthickness=0)
        bar = ttk.Scrollbar(scroll, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        bar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.cards = tk.Frame(self.canvas, bg=BG)
        self.canvas_id = self.canvas.create_window((0, 0), window=self.cards, anchor='nw')
        self.cards.bind('<Configure>', lambda _: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', self.resize)
        self.fresh = tk.Frame(self, bg=CARD)
        self.fresh.pack(fill='x', padx=24, pady=(0, 10))
        self.fresh_text = tk.Label(self.fresh, bg=CARD, fg=MUTED, anchor='w', justify='left', padx=14, pady=12)
        self.fresh_text.pack(side='left', fill='x', expand=True)
        self.fresh_btn = ttk.Button(self.fresh, text=self.t('fresh_probe'), command=lambda: self.start_probe('__fresh__'))
        self.fresh_btn.pack(side='right', padx=12)
        self.fresh_text.bind('<Button-1>', lambda _: self.details(None))
        footer = tk.Frame(self, bg=BG)
        footer.pack(fill='x', padx=24, pady=(0, 10))
        ttk.Button(footer, text=self.t('settings'), command=self.settings).pack(side='left')
        ttk.Button(footer, text=self.t('refresh'), command=self.refresh).pack(side='left', padx=8)
        ttk.Button(footer, text=self.t('integration'), command=self.integration_dialog).pack(side='left')
        ttk.Button(footer, text=self.t('quit'), command=self.quit_app).pack(side='right')
        tk.Label(footer, text=f'Windows v{FRONTEND_VERSION}' + (' · ' + self.t('demo') if self.backend.demo else ''), bg=BG, fg=MUTED).pack(side='right', padx=12)
        self.status = tk.Label(self, text=self.last_message, bg=BG, fg=MUTED, anchor='w', wraplength=760, justify='left')
        self.status.pack(fill='x', padx=24, pady=(0, 12))
        if self.snap: self.render()

    def resize(self, event):
        self.canvas.itemconfigure(self.canvas_id, width=event.width)
        self.status.config(wraplength=max(400, self.winfo_width()-48))
        if self.resize_timer: self.after_cancel(self.resize_timer)
        self.resize_timer = self.after(150, self.render_rows)

    def ensure_tray(self):
        if self.tray is None:
            from tray import Tray
            self.tray = Tray(lambda action: self.results.put(('tray', action, None, None)),
                             lambda: [self.t(k) for k in ('open','settings','quit')])

    def close(self):
        if self.prefs.values['background']:
            try:
                self.ensure_tray()
            except Exception as exc:
                messagebox.showerror(self.t('tray_error'), str(exc), parent=self)
                return
            for child in self.winfo_children():
                if isinstance(child, tk.Toplevel): child.destroy()
            self.withdraw()
        else:
            self.quit_app()

    def show(self):
        self.deiconify()
        self.lift()
        self.refresh()

    def quit_app(self):
        self.closed = True
        if self.tray:
            self.tray.close()
            self.tray = None
        self.destroy()

    def wheel(self, event):
        if event.widget.winfo_toplevel() is self:
            self.canvas.yview_scroll(-int(event.delta / 120), 'units')

    def task(self, kind, fn, key=None):
        def work():
            try: self.results.put((kind, key, fn(), None))
            except Exception as exc: self.results.put((kind, key, None, str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def refresh(self):
        if not self.loading:
            self.loading = True
            self.task('snapshot', self.backend.snapshot)

    def poll(self):
        self.refresh()
        self.after(8000, self.poll)

    def heartbeat(self):
        if self.backend.demo or self.integration_busy or time.monotonic()-self.last_heartbeat < 60:
            return
        self.last_heartbeat = time.monotonic()
        for action, sid in schedule_actions(self.snap, self.backend.pending):
            if action == 'fresh':
                self.start_probe('__fresh__')
            elif action == 'tick' and 'tick' not in self.jobs:
                self.jobs.add('tick')
                self.task('tick', lambda: self.backend.run(['tick']))
            elif action == 'reminder' and time.monotonic()-self.nudged.get(sid, -100000) > 900:
                self.nudged[sid] = time.monotonic()
                row = next(t for t in self.snap['threads'] if t['id'] == sid)
                text = self.t('reminder') + ' ' + row.get('title', sid)
                self.last_message = text
                self.task('reminder', lambda text=text: self.backend.run(['pet', 'say', text]))

    def drain(self):
        while not self.results.empty():
            kind, key, value, error = self.results.get_nowait()
            if kind == 'tray':
                if key == 'quit':
                    self.quit_app()
                    return
                self.show()
                if key == 'settings': self.settings()
                continue
            if kind == 'snapshot':
                self.loading = False
                if not error:
                    self.snap = value
                    self.render()
                    self.heartbeat()
            elif kind == 'probe':
                self.last_message = self.t('finished') + ' ' + (value or '')[-350:]
                self.refresh()
                self.render_rows()
            elif kind == 'config':
                self.busy_action = False
                if not error:
                    try:
                        self.prefs.save(*key)
                        self.language = self.prefs.values['language']
                        self.last_message = self.t('saved')
                        self.build_ui()
                    except OSError as exc: error = str(exc)
                self.refresh()
            elif kind == 'integration':
                self.integration_busy = False
                payload = value if not error else {'ok':False,'error':error}
                self.show_integration_result(payload)
                self.last_message = self.t('integration_done' if payload.get('ok') and key != 'status' else 'integration_ready' if (payload.get('status') or {}).get('ready') else 'integration_pending' if payload.get('ok') else 'integration_error')
                self.refresh()
            elif kind == 'tick':
                self.jobs.discard('tick')
            elif kind == 'notification':
                self.last_message = self.t('notice_sent')
            if error:
                self.last_message = self.t('read_failed' if kind == 'snapshot' else 'failed') + ': ' + error
            self.status.config(text=self.last_message, fg=RED if error else MUTED)
        self.after(100, self.drain)

    def render(self):
        o = self.snap.get('overall') or {}
        down, warn, up = (o.get(k, 0) for k in ('downgraded', 'suspicious', 'upgraded'))
        self.hero.config(image=self.photos['alert' if down else 'warn' if warn else 'ok'])
        headline = self.t('down_count', n=down) if down else self.t('warn_count', n=warn) if warn else self.t('no_anomaly')
        self.headline.config(text=headline, fg=RED if down else AMBER if warn else GREEN)
        self.summary.config(text=self.t('summary', warn=warn, up=up, running=o.get('running',0)))
        hooks = self.snap.get('hooks') or {}
        needs_setup = not (self.snap.get('install') or {}).get('plugin_enabled') or hooks.get('state') != 'trusted'
        self.integration_banner.config(text=self.t('integration_hint') if needs_setup and not self.backend.demo else '')
        self.account.config(text=f"{backend_text((self.snap.get('account') or {}).get('label', ''), self.language)} · Hooks: {backend_text(hooks.get('state', '—'), self.language)} · {self.t('last_hook')} {backend_text(self.snap.get('hooks_last_event_ago'), self.language) or self.t('none')}")
        label, color = probe_label(self.snap.get('global_probe'), self.language)
        running = self.snap.get('global_running') or '__fresh__' in self.backend.pending
        self.fresh_text.config(text=f"{self.t('fresh')} · {self.snap.get('default_model') or self.t('default')}\n{self.t('running') if running else label}", fg=color)
        self.fresh_btn.config(state='disabled' if running or self.backend.demo else 'normal')
        self.render_rows()
        if self.last_message == self.t('loading'): self.last_message = self.t('help')
        self.status.config(text=self.last_message)

    def render_rows(self):
        self.resize_timer = None
        for child in self.cards.winfo_children(): child.destroy()
        term = self.search.get().strip().lower()
        rows = [t for t in self.snap.get('threads', []) if term in f"{t.get('title', '')} {t.get('model', '')} {t.get('id', '')}".lower()]
        if not rows:
            tk.Label(self.cards, text=self.t('empty'), bg=BG, fg=MUTED, pady=25).pack()
        for row in rows:
            card = tk.Frame(self.cards, bg=CARD, padx=14, pady=12)
            card.pack(fill='x', pady=(0,3))
            running = row.get('probe_running') or row['id'] in self.backend.pending
            btn = ttk.Button(card, text=self.t('running' if running else 'retry' if row.get('last_failure') else 'probe'), command=lambda t=row: self.start_probe(t['id']))
            btn.pack(side='right', padx=(12,0))
            if running or row.get('halted') or row.get('unavailable') or self.backend.demo: btn.config(state='disabled')
            body = tk.Frame(card, bg=CARD)
            body.pack(side='left', fill='x', expand=True)
            label, color = probe_label(row.get('last_probe'), self.language)
            if row.get('alert'): color = RED
            lines = [(row.get('title') or row['id'], INK, True),
                     (f"{row.get('model') or self.t('unknown_model')} @ {row.get('effort') or self.t('default')} · {self.t('turns', n=row.get('turns',0))} · {backend_text(row.get('updated_ago'), self.language)}", MUTED, False),
                     ((self.t('running') + ' · ' + (backend_text(row.get('probe_note'), self.language) or self.t('collecting'))) if running else label, color, False)]
            for flag, key in [('archived','archived'),('unavailable','unavailable'),('halted','halted'),('last_failure','last_failed')]:
                if row.get(flag): lines.append((self.t(key), MUTED if flag in ('archived','unavailable') else AMBER, False))
            if row.get('due') and not running: lines.append((self.t('due'), AMBER, False))
            if row.get('last_evidence'): lines.append((backend_text(row['last_evidence'], self.language), color, False))
            for text, fg, bold in lines:
                lbl = tk.Label(body, text=text, bg=CARD, fg=fg, anchor='w', justify='left', wraplength=max(280,self.canvas.winfo_width()-165), font=('Microsoft YaHei UI',11 if bold else 10,'bold' if bold else 'normal'))
                lbl.pack(fill='x')
                lbl.bind('<Button-1>', lambda _, t=row: self.details(t['id']))

    def start_probe(self, key):
        if self.backend.demo: return
        row = next((r for r in self.snap.get('threads', []) if r['id'] == key), None)
        if key != '__fresh__' and (not row or any(row.get(k) for k in ('probe_running','halted','unavailable'))): return
        if key == '__fresh__' and self.snap.get('global_running'): return
        if not self.backend.reserve(key): return
        self.last_message = self.t('started')
        self.render()
        self.task('probe', lambda: self.backend.probe(key), key)

    def details(self, key):
        row = next((r for r in self.snap.get('threads', []) if r['id']==key), {}) if key else {}
        title = row.get('title') if key else self.t('fresh')
        probes = row.get('probes') or [] if key else self.snap.get('global_probes') or []
        report = self.t('report') + ' · ' + (title or '') + '\n\n' + self.t('history') + '\n'
        report += '\n'.join(probe_label(p,self.language)[0] + '\n  ' + json.dumps(p.get('results') or [],ensure_ascii=False) for p in probes) if probes else self.t('no_report')
        if row.get('evidence'): report += '\n\n' + self.t('evidence') + '\n' + '\n'.join(backend_text(e.get('text',''), self.language) for e in row['evidence'])
        failure = row.get('last_failure') if key else self.snap.get('global_failure')
        if failure: report += '\n\n' + self.t('error') + '\n' + '\n'.join(failure.get('errors') or [])
        win = tk.Toplevel(self); win.title(title or self.t('report')); win.geometry('780x650'); win.minsize(480,360)
        text = tk.Text(win, wrap='word', bg=BG, fg=INK, relief='flat', padx=20, pady=20)
        bar = ttk.Scrollbar(win,command=text.yview); text.configure(yscrollcommand=bar.set)
        bar.pack(side='right',fill='y'); text.pack(fill='both',expand=True)
        text.insert('1.0',report); text.config(state='disabled')
        def copy(): self.clipboard_clear(); self.clipboard_append(report)
        ttk.Button(win,text=self.t('copy'),command=copy).pack(pady=10)

    def integration_dialog(self):
        if self.integration_window and self.integration_window.winfo_exists():
            self.integration_window.lift()
            return
        win = self.integration_window = tk.Toplevel(self)
        win.title(self.t('integration'))
        win.geometry('920x710'); win.minsize(760,560); win.configure(bg=BG)
        tk.Label(win,text=self.t('integration_intro'),wraplength=850,justify='left',bg=BG).pack(fill='x',padx=20,pady=(15,6))
        tk.Label(win,text=self.t('integration_storage' if FROZEN else 'integration_storage_source'),wraplength=850,justify='left',bg=BG,fg=MUTED).pack(fill='x',padx=20,pady=6)
        self.trust_install = tk.BooleanVar(value=False)
        tk.Checkbutton(win,text=self.t('trust_with_install'),variable=self.trust_install,bg=BG,anchor='w').pack(fill='x',padx=20,pady=8)
        bar=tk.Frame(win,bg=BG); bar.pack(fill='x',padx=20,pady=5)
        self.integration_buttons=[]
        for title, action in [('install_hooks','install'),('trust_hooks','trust'),('diagnose','status')]:
            button=ttk.Button(bar,text=self.t(title),command=lambda action=action:self.integration_action(action))
            button.pack(side='left',padx=(0,8)); self.integration_buttons.append(button)
        def choose():
            selected=filedialog.askopenfilename(parent=win,title=self.t('choose_codex'),filetypes=[('Codex executable','*.exe')])
            if selected: self.integration_action('set-codex',path=selected)
        button=ttk.Button(bar,text=self.t('choose_codex'),command=choose)
        button.pack(side='left'); self.integration_buttons.append(button)
        self.integration_summary=tk.Label(win,text=self.t('integration_busy'),bg=BG,fg=MUTED,anchor='w',wraplength=850)
        self.integration_summary.pack(fill='x',padx=20,pady=8)
        self.integration_text=tk.Text(win,wrap='word',height=16,bg=CARD,fg=INK,relief='flat',padx=12,pady=10)
        self.integration_text.pack(fill='both',expand=True,padx=20,pady=5)
        self.integration_text.config(state='disabled')
        def copy():
            self.clipboard_clear(); self.clipboard_append(self.integration_text.get('1.0','end-1c'))
        ttk.Button(win,text=self.t('integration_copy'),command=copy).pack(pady=12)
        if self.backend.demo:
            self.show_integration_result(self.backend.integration('status'))
        elif not self.integration_busy:
            self.integration_action('status')
        else:
            for button in self.integration_buttons: button.config(state='disabled')

    def integration_action(self, action, path=None):
        if self.integration_busy or self.backend.demo: return
        self.integration_busy=True
        self.integration_summary.config(text=self.t('integration_busy'),fg=MUTED)
        for button in self.integration_buttons: button.config(state='disabled')
        trust=bool(action=='install' and self.trust_install.get())
        self.task('integration',lambda:self.backend.integration(action,trust=trust,path=path),action)

    def show_integration_result(self, result):
        if not self.integration_window or not self.integration_window.winfo_exists(): return
        for button in self.integration_buttons: button.config(state='disabled' if self.backend.demo else 'normal')
        status=result.get('status') or {}
        self.integration_summary.config(text=self.t('integration_error') if not result.get('ok') else self.t('integration_ready') if status.get('ready') else self.t('integration_pending'),fg=GREEN if status.get('ready') else AMBER)
        lines=[]
        if status:
            lines.append('Codex: '+str(status.get('codex_bin') or '—'))
            for key,label in [('manual_probe_available','integration_manual'),('plugin_enabled','integration_installed'),('runtime_ready','integration_runtime'),('restart_required','integration_restart')]:
                lines.append(self.t(label)+': '+self.t('yes' if status.get(key) else 'no'))
            lines.append('Hooks: '+str((status.get('hooks') or {}).get('state') or '—'))
        lines.append(json.dumps(result,ensure_ascii=False,indent=2))
        self.integration_text.config(state='normal'); self.integration_text.delete('1.0','end')
        self.integration_text.insert('1.0','\n'.join(lines)); self.integration_text.config(state='disabled')

    def settings(self):
        win = tk.Toplevel(self); win.title(self.t('settings')); win.geometry('600x770'); win.minsize(550,730); win.configure(bg=BG)
        cfg = self.snap.get('config') or {}
        fields = {}
        def choice(key, values, current):
            frame=tk.Frame(win,bg=BG); frame.pack(fill='x',padx=24,pady=5)
            tk.Label(frame,text=self.t(key),bg=BG).pack(side='left')
            labels = [('简体中文' if v=='zh' else 'English') if key=='language' else self.t(v) if v in ('auto','nudge','manual','15m','30m','1h') else self.t('every8') if v=='turns:8' else v for v in values]
            var=tk.StringVar(value=labels[values.index(current)] if current in values else current)
            if current not in values: values=[*values,current]; labels=[*labels,current]
            ttk.Combobox(frame,textvariable=var,values=labels,state='readonly',width=29).pack(side='right')
            fields[key]=(var,dict(zip(labels,values)))
        choice('language',['zh','en'],self.language)
        choice('mode',['auto','nudge'],cfg.get('mode','auto'))
        choice('frequency',['manual','15m','30m','1h','turns:8'],cfg.get('frequency','30m'))
        choice('fresh_frequency',['manual','15m','30m','1h'],cfg.get('fresh_frequency','manual'))
        tk.Label(win,text=self.t('schedule_hint'),wraplength=530,justify='left',bg=BG,fg=MUTED).pack(padx=24,pady=10)
        flags={}
        for key in ('notify','notify_on_ok','sound','hide_titles','show_inactive_threads','background'):
            var=tk.BooleanVar(value=self.prefs.values['background'] if key=='background' else bool(cfg.get(key)))
            flags[key]=var
            tk.Checkbutton(win,text=self.t(key),variable=var,bg=BG,anchor='w').pack(fill='x',padx=24,pady=3)
        def save():
            if self.busy_action or self.backend.demo: return
            chosen={k:m[v.get()] for k,(v,m) in fields.items()}
            language=chosen.pop('language'); background=flags['background'].get()
            # Older installed hooks schedule fresh probes independently of mode.
            if chosen.get('mode') == 'nudge': chosen['fresh_frequency'] = 'manual'
            if background:
                try: self.ensure_tray()
                except Exception as exc: messagebox.showerror(self.t('tray_error'),str(exc),parent=win); return
            edits={**chosen,**{k:str(v.get()).lower() for k,v in flags.items() if k!='background'}}
            self.busy_action=True
            self.task('config',lambda:[self.backend.run(['config','set',k,v]) for k,v in edits.items()],(language,background))
            win.destroy()
        ttk.Button(win,text=self.t('test_notification'),command=lambda:self.task('notification',lambda:self.backend.run(['pet','say',self.t('test_notice')])),state='disabled' if self.backend.demo else 'normal').pack(pady=10)
        ttk.Button(win,text=self.t('save'),command=save,state='disabled' if self.backend.demo else 'normal').pack(pady=10)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--demo',action='store_true')
    parser.add_argument('--smoke-test',action='store_true')
    args=parser.parse_args()
    # Even demo snapshots write state. Keep previews/tests out of the user's ledger.
    temp = tempfile.TemporaryDirectory(prefix='nerfed-preview-') if args.demo or args.smoke_test else None
    if temp:
        os.environ['CODEX_HOME']=temp.name
        os.environ['NERFED_HOME']=str(Path(temp.name)/'ledger')
    app=Panel(demo=args.demo or args.smoke_test)
    smoke_ok=False
    if args.smoke_test:
        deadline=time.monotonic()+40
        def check():
            nonlocal smoke_ok
            if app.loading and time.monotonic()<deadline: app.after(100,check); return
            if not app.snap.get('threads'): app.quit_app(); return
            for language in ('zh','en'):
                app.language=language; app.build_ui(); app.geometry('680x640'); app.update()
                app.details(app.snap['threads'][0]['id']); app.settings(); app.integration_dialog(); app.update_idletasks()
                for child in app.winfo_children():
                    if isinstance(child,tk.Toplevel): child.destroy()
            app.ensure_tray()
            app.prefs.values['background']=True
            app.close(); app.update(); assert app.state()=='withdrawn'
            app.show(); app.update(); assert app.state()!='withdrawn'
            smoke_ok=True
            app.after(500,app.quit_app)
        app.after(200,check)
    try: app.mainloop()
    finally:
        if temp: temp.cleanup()
    if args.smoke_test and not smoke_ok: raise SystemExit(1)

if __name__=='__main__': main()

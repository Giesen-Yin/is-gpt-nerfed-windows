"""User-triggered Windows integration. Native Codex CLI owns registration and hook trust.

The GUI bundle is copied to a content-addressed per-user runtime before registration.
Hooks never depend on Python on PATH or the location of the portable GUI.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib

EVENTS = ('SessionStart', 'UserPromptSubmit', 'PreToolUse', 'Stop', 'SessionEnd')


def quote_ps(value):
    return "'" + str(value).replace("'", "''") + "'"


def encoded_hook_command(setup):
    """Both source and frozen hooks fail open; intentional halts use stdout JSON, not exit 2."""
    script = "$ErrorActionPreference='Stop'\ntry {\n" + setup + r"""
  if (-not [IO.File]::Exists($exe)) { exit 0 }
  $utf8=[Text.UTF8Encoding]::new($false)
  [Console]::OutputEncoding=$utf8
  [Console]::InputEncoding=$utf8
  $psi=[Diagnostics.ProcessStartInfo]::new()
  $psi.FileName=$exe
  $psi.Arguments=$arguments
  $psi.UseShellExecute=$false
  $psi.CreateNoWindow=$true
  $psi.RedirectStandardInput=$true
  $psi.RedirectStandardOutput=$true
  $psi.RedirectStandardError=$true
  $psi.StandardOutputEncoding=$utf8
  $psi.StandardErrorEncoding=$utf8
  $p=[Diagnostics.Process]::new()
  $p.StartInfo=$psi
  [void]$p.Start()
  $out=$p.StandardOutput.ReadToEndAsync()
  $err=$p.StandardError.ReadToEndAsync()
  $bytes=$utf8.GetBytes([Console]::In.ReadToEnd())
  $p.StandardInput.BaseStream.Write($bytes,0,$bytes.Length)
  $p.StandardInput.BaseStream.Flush()
  $p.StandardInput.Close()
  $p.WaitForExit()
  $output=$out.GetAwaiter().GetResult()
  $errorText=$err.GetAwaiter().GetResult()
  $code=$p.ExitCode
  $p.Dispose()
  [Console]::Error.Write($errorText)
  if ($code -eq 0) { [Console]::Out.Write($output) }
  # Backend crashes or missing imports must never block Codex. Valid JSON denials are preserved.
  exit 0
} catch {
  [Console]::Error.WriteLine('is-gpt-nerfed hook launcher: '+$_.Exception.Message)
  exit 0
}
"""
    encoded = base64.b64encode(script.encode('utf-16-le')).decode('ascii')
    return 'powershell.exe -NoProfile -NonInteractive -EncodedCommand ' + encoded


def hook_command(command, event, codex_home, ledger, plugin):
    arguments = subprocess.list2cmdline([*command[1:], 'hook', '--event', event])
    setup = f"""  $env:CODEX_HOME={quote_ps(codex_home)}
  $env:NERFED_HOME={quote_ps(ledger)}
  $env:PLUGIN_ROOT={quote_ps(plugin)}
  $exe={quote_ps(command[0])}
  $arguments={quote_ps(arguments)}
"""
    if len(command)>1:
        setup += f"  if (-not [IO.File]::Exists({quote_ps(command[1])})) {{ exit 0 }}\n"
    return encoded_hook_command(setup)


def source_hook_command(event):
    """Portable source manifest: recover a stale cache path and tolerate no system Python."""
    setup = r"""  $roots=@($env:PLUGIN_ROOT,$env:CLAUDE_PLUGIN_ROOT)
  if ($env:NERFED_HOME) { $roots += [IO.Path]::Combine($env:NERFED_HOME,'plugin') }
  $codexHome=if ($env:CODEX_HOME) { $env:CODEX_HOME } else { [IO.Path]::Combine($env:USERPROFILE,'.codex') }
  $roots += [IO.Path]::Combine($codexHome,'is-gpt-nerfed','plugin')
  $scriptPath=$null
  foreach ($root in $roots) {
    if (-not $root) { continue }
    $candidate=[IO.Path]::Combine($root,'skills','is-gpt-nerfed','scripts','nerfed')
    if ([IO.File]::Exists($candidate)) { $scriptPath=$candidate; $env:PLUGIN_ROOT=$root; break }
  }
  if (-not $scriptPath) { exit 0 }
  $python=Get-Command python.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
  $prefix=''
  if (-not $python) {
    $python=Get-Command py.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $prefix='-3 '
  }
  if (-not $python) { exit 0 }
  $exe=$python.Source
"""
    setup += "  $arguments=$prefix+'-X utf8 \"'+$scriptPath+'\" hook --event " + event + "'\n"
    return encoded_hook_command(setup)


def hook_is_fail_open(command):
    try:
        script = base64.b64decode(command.split('-EncodedCommand ',1)[1],validate=True).decode('utf-16-le')
        return 'exit 0' in script and 'exit $code' not in script and 'PLUGIN_ROOT' in script
    except (ValueError, UnicodeError, IndexError):
        return False


def stage_runtime(m):
    """Publish a complete runtime atomically; leave old runtime versions for in-flight hooks."""
    plugin_source = Path(m.HERE).parents[2]  # bundled/source plugin, never trust a stale PLUGIN_ROOT override
    if m.FROZEN:
        exe_source = Path(sys.executable).resolve()
        bundle = exe_source.parent
        inputs = [exe_source, *(p for p in (bundle/'_internal').rglob('*') if p.is_file() and '__pycache__' not in p.parts)]
        if not (bundle/'_internal').is_dir():
            raise RuntimeError('Incomplete portable bundle: missing _internal')
    else:
        exe_source = Path(sys.executable).resolve()
        bundle = plugin_source.parent
        inputs = [p for p in plugin_source.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    digest = hashlib.sha256()
    for path in sorted(inputs):
        relative = path.relative_to(bundle) if path.is_relative_to(bundle) else path.name
        digest.update(str(relative).encode('utf8'))
        digest.update(path.read_bytes())
    digest.update(str(exe_source).encode('utf8') if not m.FROZEN else b'frozen')
    # Home paths are embedded in the hook commands; a home move requires newly generated commands.
    digest.update((m.CODEX_HOME + m.NERFED_HOME).encode('utf8'))
    target = Path(m.NERFED_HOME).resolve()/'windows-runtime'/f'{m.VERSION}-{digest.hexdigest()[:16]}'
    market = target/'marketplace'
    backend_exe = target/'nerfed-backend.exe'
    if not (target/'complete.json').is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = Path(tempfile.mkdtemp(prefix='.staging-', dir=target.parent))
        try:
            if m.FROZEN:
                shutil.copy2(exe_source, temp/'nerfed-backend.exe')
                shutil.copytree(bundle/'_internal', temp/'_internal', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            shutil.copytree(plugin_source, temp/'marketplace/plugin', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            manifest_file = temp/'marketplace/plugin/.codex-plugin/plugin.json'
            manifest = json.loads(manifest_file.read_text(encoding='utf8'))
            command = [str(backend_exe)] if m.FROZEN else [str(exe_source), str(market/'plugin/skills/is-gpt-nerfed/scripts/nerfed')]
            for event, groups in manifest['hooks']['hooks'].items():
                if event not in EVENTS:
                    raise RuntimeError('Unexpected hook event: ' + event)
                for group in groups:
                    for hook in group['hooks']:
                        hook['command'] = hook_command(command, event, m.CODEX_HOME, m.NERFED_HOME, market/'plugin')
            manifest_file.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
            marketplace = {'name': m.MARKETPLACE_NAME, 'interface': {'displayName': 'Is GPT nerfed? · Windows'},
                           'plugins':[{'name':m.PLUGIN_NAME,'source':{'source':'local','path':'./plugin'},
                                       'policy':{'installation':'AVAILABLE','authentication':'ON_INSTALL'},'category':'Developer Tools'}]}
            m.write_json(str(temp/'marketplace/.agents/plugins/marketplace.json'), marketplace)
            m.write_json(str(temp/'complete.json'), {'version':m.VERSION,'frozen':m.FROZEN,'runtime':str(target)})
            # Retain the CLI's normal path inside the skill but tell agents how to launch the bundled runtime.
            skill = temp/'marketplace/plugin/skills/is-gpt-nerfed/SKILL.md'
            text = skill.read_text(encoding='utf8')
            text += '\n\n## Windows application runtime\n\nUse this command prefix instead of executing the extensionless Python script directly:\n\n```powershell\n& ' + quote_ps(command[0]) + (' ' + quote_ps(command[1]) if len(command)>1 else '') + '\n```\n'
            skill.write_text(text, encoding='utf8')
            if target.exists():
                raise RuntimeError('Incomplete runtime already exists: ' + str(target))
            os.replace(temp, target)
        finally:
            if temp.exists():
                shutil.rmtree(temp)
    manifest = json.loads((market/'plugin/.codex-plugin/plugin.json').read_text(encoding='utf8'))
    commands = [h['command'] for groups in manifest['hooks']['hooks'].values() for group in groups for h in group['hooks']]
    return {'runtime':str(target),'marketplace':str(market),'plugin':str(market/'plugin'),
            'version':m.VERSION,'standalone':m.FROZEN,'commands':commands}


def status(m, live=False):
    cfg = m.load_config()
    cb = m.codex_bin(cfg)
    installed = m.read_json(str(Path(m.NERFED_HOME)/'windows-install.json'), {}) or {}
    hooks = m.hooks_status(cfg, force=live)
    bank = Path(m.BANK_PATH)
    provenance = m.read_json(str(bank.with_name('provenance.json')), {}) or {}
    bank_ok = bank.is_file() and hashlib.sha256(bank.read_bytes().replace(b'\r\n',b'\n')).hexdigest() == provenance.get('sha256')
    runtime = installed.get('runtime')
    runtime_ready = bool(runtime and (Path(runtime)/'complete.json').is_file() and (Path(runtime)/'marketplace/plugin/.codex-plugin/plugin.json').is_file())
    if runtime_ready and installed.get('standalone'):
        runtime_ready = (Path(runtime)/'nerfed-backend.exe').is_file() and (Path(runtime)/'_internal').is_dir()
    definition_match = None
    if live and cb and installed.get('commands'):
        actual = m.cas.list_plugin_hooks(cb, m.PLUGIN_NAME)['hooks']
        expected = set(installed['commands'])
        definition_match = {h.get('command') for h in actual if h.get('command') in expected} == expected
    enabled = m.plugin_enabled_in_config()
    ready = bool(cb and bank_ok and enabled and runtime_ready and installed.get('version') == m.VERSION and definition_match is not False and hooks.get('state')=='trusted' and not hooks.get('disabled') and not hooks.get('error'))
    last_event = (m.tail_jsonl(m.EVENTS_PATH, 1) or [{}])[-1]
    last_error = None
    try:
        from collections import deque
        with open(m.ERRORS_PATH, encoding='utf8') as stream:
            last_error = next(iter(deque(stream, maxlen=1)), '').strip() or None
    except OSError:
        pass
    return {'last_hook_event':{k:last_event.get(k) for k in ('ts','event','sid')},'last_error':last_error,'version':m.VERSION,'codex_bin':cb,'codex_version':m.codex_version(cb),'bank_ok':bank_ok,
            'plugin_enabled':enabled,'hooks':hooks,'runtime':runtime,'runtime_ready':runtime_ready,
            'installed_version':installed.get('version'),'definition_match':definition_match,'standalone':bool(installed.get('standalone')),
            'restart_required':bool(ready and not hooks.get('desktop_loaded_current')),
            'ready':ready,'manual_probe_available':bool(cb and bank_ok), 'events':list(EVENTS),
            'codex_home':m.CODEX_HOME,'ledger':m.NERFED_HOME, 'installed':installed}


def checked_run(m, cb, args, logs):
    rc, output = m.run([cb, *args])
    logs.append({'command':args, 'returncode':rc, 'output':output})
    if rc:
        raise RuntimeError('Codex ' + ' '.join(args[:3]) + ' failed: ' + output)
    return output


def install(m, trust=False):
    cfg = m.load_config()
    cb = m.codex_bin(cfg)
    logs = []
    if not cb:
        raise RuntimeError('Codex executable not found. Choose codex.exe in the application first.')
    checked_run(m, cb, ['--version'], logs)
    # Verify app-server compatibility before any configuration changes.
    m.cas.list_plugin_hooks(cb, m.PLUGIN_NAME)
    staged = stage_runtime(m)
    config_path = Path(m.CODEX_HOME)/'config.toml'
    previous = tomllib.loads(config_path.read_text(encoding='utf8')) if config_path.exists() else {}
    old_market = (previous.get('marketplaces') or {}).get(m.MARKETPLACE_NAME) or {}
    old_plugin = (previous.get('plugins') or {}).get(f'{m.PLUGIN_NAME}@{m.MARKETPLACE_NAME}')
    selector = f'{m.PLUGIN_NAME}@{m.MARKETPLACE_NAME}'
    receipt = Path(m.NERFED_HOME)/'windows-install.json'
    previous_receipt = m.read_json(str(receipt))
    try:
        checked_run(m, cb, ['plugin','marketplace','add',staged['marketplace']], logs)
        # Codex may retain the same-version cache; native uninstall/reinstall refreshes it.
        if old_plugin is not None:
            checked_run(m, cb, ['plugin','remove',selector], logs)
        checked_run(m, cb, ['plugin','add',selector], logs)
        listed = m.cas.list_plugin_hooks(cb, m.PLUGIN_NAME)
        hooks = listed['hooks']
        if any(n.get('kind') == 'error' for n in listed.get('notes') or []):
            raise RuntimeError('Codex could not load the plugin: ' + str(listed['notes']))
        expected = set(staged['commands'])
        ours = [h for h in hooks if h.get('command') in expected]
        if len(ours) != len(EVENTS) or {h.get('command') for h in ours} != expected:
            raise RuntimeError(f'Expected {len(EVENTS)} newly installed hooks; Codex listed {len(ours)} matching definitions. No unknown hook was trusted.')
        if trust:
            m.cas.trust_hooks(cb, ours)
            verified = m.cas.list_plugin_hooks(cb, m.PLUGIN_NAME)['hooks']
            verified = [h for h in verified if h.get('command') in expected]
            if len(verified) != len(EVENTS) or {h.get('command') for h in verified} != expected or any(h.get('trustStatus') != 'trusted' or h.get('enabled') is False for h in verified):
                raise RuntimeError('Codex did not confirm all five hooks as enabled and trusted.')
        staged['installed_at'] = m.iso()
        m.write_json(str(Path(m.NERFED_HOME)/'windows-install.json'), staged)
        m.hooks_status(cfg, force=True)
        m.log_event('windows_install', runtime=staged['runtime'], trust=trust, version=m.VERSION)
        return {'ok':True,'status':status(m),'logs':logs,'message':'Installed. Restart Codex to reload hooks.' if trust else 'Installed. Trust the hooks in the application, then restart Codex.'}
    except Exception as exc:
        # Restore this plugin via its native owner. Do not overwrite the whole user's config.toml.
        rollback = []
        try:
            if old_market.get('source'):
                checked_run(m, cb, ['plugin','marketplace','add',str(old_market['source'])], rollback)
                if old_plugin is not None:
                    m.run([cb,'plugin','remove',selector])
                    checked_run(m, cb, ['plugin','add',selector], rollback)
                    if old_plugin.get('enabled') is False:
                        app=m.cas.AppServer(cb, hooks_enabled=True)
                        try:
                            app.initialize()
                            app.request('config/batchWrite',{'edits':[{'keyPath':f'plugins."{selector}".enabled','mergeStrategy':'upsert','value':False}],'reloadUserConfig':True},30)
                        finally: app.close()
            elif old_plugin is None:
                m.run([cb,'plugin','remove',selector])
                checked_run(m,cb,['plugin','marketplace','remove',m.MARKETPLACE_NAME],rollback)
        except Exception as restore_error:
            rollback.append({'error':str(restore_error)})
        if previous_receipt is not None:
            m.write_json(str(receipt),previous_receipt)
        elif receipt.exists():
            receipt.unlink()
        return {'ok':False,'error':str(exc),'logs':logs,'rollback':rollback}


def trust_installed(m):
    installed=m.read_json(str(Path(m.NERFED_HOME)/'windows-install.json'),{}) or {}
    expected=set(installed.get('commands') or [])
    if len(expected)!=len(EVENTS):
        raise RuntimeError('Install/update using this application before trusting its hooks.')
    cb=m.codex_bin(m.load_config())
    if not cb: raise RuntimeError('Codex executable not found')
    hooks=m.cas.list_plugin_hooks(cb,m.PLUGIN_NAME)['hooks']
    ours=[h for h in hooks if h.get('command') in expected]
    if len(ours)!=len(EVENTS) or {h.get('command') for h in ours} != expected: raise RuntimeError('Installed hook definitions changed. Install/update again before trusting them.')
    m.cas.trust_hooks(cb,ours)
    return {'ok':True,'status':status(m,live=True),'message':'Hooks trusted. Restart Codex.'}


def command(m, args):
    try:
        if args.action=='install':
            with m.locked_session("__windows_integration__"):
                result=install(m, bool(args.trust_hooks))
        elif args.action=='trust':
            with m.locked_session("__windows_integration__"):
                result=trust_installed(m)
        elif args.action=='set-codex':
            path=str(Path(args.path).resolve()) if args.path else None
            if not m._runnable_codex(path): raise RuntimeError('Select a valid native codex.exe')
            rc,out=m.run([path,'--version'],timeout=10)
            if rc or 'codex' not in out.lower(): raise RuntimeError('Selected executable did not identify itself as Codex: '+out)
            cfg=m.load_config(); cfg['codex_bin']=path; m.save_config(cfg)
            result={'ok':True,'status':status(m,live=True)}
        elif args.action=='prepare':
            # Produces runtime only, for isolated distribution checks; never registers/trusts hooks.
            result={'ok':True,'prepared':stage_runtime(m)}
        else:
            result={'ok':True,'status':status(m,live=True)}
    except Exception as exc:
        result={'ok':False,'error':str(exc)}
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result.get('ok') else 1

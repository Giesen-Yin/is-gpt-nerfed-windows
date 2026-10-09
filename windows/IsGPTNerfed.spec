# Build with: python -m PyInstaller --noconfirm windows/IsGPTNerfed.spec
from pathlib import Path
import json
import re
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct
root = Path(SPECPATH).parent
scripts = root / 'plugin/skills/is-gpt-nerfed/scripts'
version = json.loads((root / 'plugin/.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version']
backend_version = re.search(r'^VERSION = "([^"]+)"', (scripts / 'nerfed').read_text(encoding='utf-8'), re.M).group(1)
if backend_version != version:
    raise ValueError(f'Manifest version {version} differs from backend {backend_version}')
# Windows fixed version fields are numeric; display strings retain the platform suffix.
match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?", version)
if not match:
    raise ValueError(f'Unsupported release version: {version}')
version_tuple = tuple(map(int, match.groups())) + (0,)
def version_info(filename):
    return VSVersionInfo(
        ffi=FixedFileInfo(filevers=version_tuple, prodvers=version_tuple, mask=0x3f,
                          flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
        kids=[StringFileInfo([StringTable('040904B0', [
            StringStruct('FileDescription', 'Is GPT nerfed?'),
            StringStruct('FileVersion', version), StringStruct('ProductVersion', version),
            StringStruct('ProductName', 'Is GPT nerfed?'),
            StringStruct('OriginalFilename', filename),
        ])]), VarFileInfo([VarStruct('Translation', [1033, 1200])])])
# Exclude interpreter caches and local state; ship only repository-owned plugin assets.
data = [(str(p), str(p.parent.relative_to(root))) for p in (root / 'plugin').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
data += [(str(root / f'docs/face-{state}.png'), 'docs') for state in ('ok', 'warn', 'alert')]
data += [(str(root / 'LICENSE'), '.')]
data += [(str(root / 'windows/assets/chip.ico'), 'windows/assets')]
data += [(str(root / 'THIRD_PARTY_NOTICES.md'), '.')]
data += [(str(p), 'licenses') for p in (root/'windows/licenses').glob('*.txt')]
backend = Analysis([str(scripts / 'nerfed')], pathex=[str(scripts)], datas=data, hiddenimports=['sqlite3', 'winsound'], excludes=['pytest', 'IPython', 'numpy', 'pandas'])
bpyz = PYZ(backend.pure)
bexe = EXE(bpyz, backend.scripts, [], exclude_binaries=True, name='nerfed-backend', icon=str(root/'windows/assets/chip.ico'), version=version_info('nerfed-backend.exe'), console=True, upx=False)
gui = Analysis([str(root / 'windows/app.py')], pathex=[str(root / 'windows')], excludes=['pytest', 'IPython', 'numpy', 'pandas'])
gpyz = PYZ(gui.pure)
gexe = EXE(gpyz, gui.scripts, [], exclude_binaries=True, name='IsGPTNerfed', icon=str(root/'windows/assets/chip.ico'), version=version_info('IsGPTNerfed.exe'), console=False, upx=False)
app = COLLECT(gexe, bexe, gui.binaries, backend.binaries, gui.datas, backend.datas, name='IsGPTNerfed', upx=False)

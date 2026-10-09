"""Package a verified bundle and navigable docs using the manifest's version."""
import hashlib
import json
from pathlib import Path
import shutil


def copy_release_documents(root, destination):
    paths = [Path(name) for name in ('README.md','README.zh-CN.md','CHANGELOG.md','LICENSE','THIRD_PARTY_NOTICES.md','windows/README.md',
             'plugin/assets/modeltrace/provenance.json','plugin/assets/modeltrace/LICENSE-ModelTrace.txt',
             'plugin/skills/is-gpt-nerfed/scripts/vendor/LICENSE-simple-term-menu.txt')]
    paths += [p.relative_to(root) for p in (root/'docs').glob('*.md')]
    paths += [Path('docs/windows-panel.png')]
    for relative in paths:
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root/relative, target)


def package(root):
    version = json.loads((root/'plugin/.codex-plugin/plugin.json').read_text(encoding='utf8'))['version']
    release = root/'dist/releases'/version
    copy_release_documents(root, release/'IsGPTNerfed')
    archive = Path(shutil.make_archive(str(root/'dist'/f'IsGPTNerfed-Windows-v{version}'), 'zip', release, 'IsGPTNerfed'))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    print(f'Packaged {archive} ({archive.stat().st_size / 1024**2:.1f} MiB)')
    return archive


if __name__ == '__main__':
    package(Path(__file__).resolve().parents[1])

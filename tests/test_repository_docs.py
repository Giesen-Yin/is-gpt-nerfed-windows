import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
FILES=('README.md','README.zh-CN.md','CHANGELOG.md','docs/DEVELOPMENT.md','docs/VERIFICATION.md','docs/UPSTREAM_REVIEW.md','windows/README.md')

def broken_links(root):
    broken=[]
    for name in FILES:
        path=root/name
        for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',path.read_text(encoding='utf8')):
            target=target.strip('<>').split('#',1)[0]
            if not target or re.match(r'\w+://',target): continue
            if not (path.parent/target).exists(): broken.append((name,target))
    return broken

class DocumentationTests(unittest.TestCase):
    def test_readmes_identify_fork_changes_upstream_and_changelog(self):
        for name in ('README.md','README.zh-CN.md'):
            text=(ROOT/name).read_text(encoding='utf8')
            for required in ('https://github.com/kiyoakii/is-gpt-nerfed','CHANGELOG.md','Added','Changed','Removed','Preserved','MIT'):
                self.assertIn(required,text,(name,required))
        self.assertFalse(broken_links(ROOT))

    def test_release_documentation_links_resolve(self):
        spec=importlib.util.spec_from_file_location('package_release',ROOT/'windows/package_release.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)
            module.copy_release_documents(ROOT,dest)
            self.assertFalse(broken_links(dest),broken_links(dest))
            self.assertEqual((dest/'LICENSE').read_bytes(),(ROOT/'LICENSE').read_bytes())

    def test_version_and_minimum_python_messages_are_consistent(self):
        version=json.loads((ROOT/'plugin/.codex-plugin/plugin.json').read_text(encoding='utf8'))['version']
        self.assertIn(f'## {version}',(ROOT/'CHANGELOG.md').read_text(encoding='utf8'))
        for path in ('install.ps1','uninstall.ps1'):
            text=(ROOT/path).read_text(encoding='utf8')
            self.assertIn('Python 3.11+',text)
            self.assertIn('sys.version_info >= (3,11)',text)

if __name__=='__main__':unittest.main()

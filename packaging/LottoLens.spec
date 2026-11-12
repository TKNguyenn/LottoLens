# Build explicitly allowlisted resources; never collect the workspace or user data.
from pathlib import Path
root = Path(SPECPATH).parent
assets = root / 'docs' / 'redesign' / 'assets'
guide = root / 'docs' / 'redesign' / 'onboarding' / 'assets'
files = [root/'LICENSE', root/'COPYRIGHT', root/'POLICY.md', *assets.glob('icon-*.svg'),
         assets/'generated/07-ticket-gold.ico', assets/'generated/07-ticket-gold.png',
         guide/'guide.json', *guide.glob('*.webp')]
datas = [(str(file), str(file.parent.relative_to(root))) for file in files]
a = Analysis([str(root/'packaging/entry.py')], pathex=[str(root)], binaries=[], datas=datas,
             hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=['tkinter'], noarchive=False)
assert not any('poppler' in source.lower() for _, source, _ in a.binaries), 'Build PATH contaminated by Poppler'
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='LottoLens', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=False,
          icon=str(assets/'generated/07-ticket-gold.ico'), version=str(root/'build/version-info.txt'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='LottoLens')

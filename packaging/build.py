"""Build an offline Windows x64 setup; tools only, no application config read."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import __version__


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--iscc', type=Path, default=ROOT/'build/tools/InnoSetup/ISCC.exe')
    args = parser.parse_args()
    compiler = args.iscc if args.iscc.is_file() else shutil.which('ISCC.exe')
    if not compiler:
        raise SystemExit('Install Inno Setup and supply --iscc PATH/ISCC.exe.')
    version = tuple(int(part) for part in __version__.split('.')) + (0,)
    (ROOT/'build').mkdir(exist_ok=True)
    (ROOT/'build/version-info.txt').write_text(
        f"VSVersionInfo(ffi=FixedFileInfo(filevers={version!r}, prodvers={version!r}, mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)), "
        f"kids=[StringFileInfo([StringTable('040904B0',[StringStruct('CompanyName','LottoLens'),StringStruct('FileDescription','LottoLens desktop'),StringStruct('FileVersion','{__version__}'),StringStruct('ProductName','LottoLens'),StringStruct('ProductVersion','{__version__}'),StringStruct('OriginalFilename','LottoLens.exe')])]), VarFileInfo([VarStruct('Translation',[1033,1200])])])",
        encoding='utf-8')
    # Qt uses Windows ICU; build tools on PATH can supply incompatible DLLs with the same name.
    environment = dict(os.environ)
    windows = Path(os.environ['SystemRoot'])
    environment['PATH'] = os.pathsep.join(map(str, [Path(sys.executable).parent, windows/'System32', windows]))
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    '--distpath', str(ROOT/'dist'), '--workpath', str(ROOT/'build/pyinstaller'),
                    str(ROOT/'packaging/LottoLens.spec')], cwd=ROOT, env=environment, check=True)
    subprocess.run([str(compiler), '/DAppVersion='+__version__, str(ROOT/'packaging/LottoLens.iss')], cwd=ROOT, check=True)
    setup = ROOT/'dist'/f'LottoLens-Setup-{__version__}.exe'
    checksum = hashlib.file_digest(setup.open('rb'), 'sha256').hexdigest()
    setup.with_suffix('.exe.sha256').write_text(checksum+'  '+setup.name+'\n', encoding='ascii')
    print(str(setup))


if __name__ == '__main__':
    main()

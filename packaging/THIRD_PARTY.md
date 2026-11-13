# Third-party software in the Windows installer

LottoLens is GPL-3.0-only. The installer includes the upstream components below. Their copyright and license terms remain in effect. The installed `third-party` directory includes license texts from the build environment.

| Component | Source and license information |
| --- | --- |
| Qt 6.11.2 | [Qt 6.11.2 source](https://download.qt.io/official_releases/qt/6.11/6.11.2/submodules/), [Qt licensing](https://doc.qt.io/qt-6.11/licensing.html) and [third-party notices by module](https://doc.qt.io/qt-6.11/licenses-used-in-qt.html). Qt libraries are distributed under GPLv3-compatible terms. |
| PySide6 and Shiboken6 6.11.2 | [Qt for Python corresponding source and license texts](https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/), offered under GPLv3 as part of this distribution. |
| CPython and bundled libraries | See the installed Python license and [CPython 3.11.9 source](https://www.python.org/downloads/release/python-3119/). Windows dependencies are listed in [CPython's build sources](https://github.com/python/cpython/blob/v3.11.9/PCbuild/get_externals.bat). |
| PyInstaller 6.22.3 | [PyInstaller source and notices](https://github.com/pyinstaller/pyinstaller/tree/v6.22.3). The bootloader exception and runtime-hook terms are in the installed PyInstaller license. |
| Inno Setup 6.7.4 | [Inno Setup source](https://github.com/jrsoftware/issrc) and [license](https://jrsoftware.org/files/is/license.txt). The Windows setup uses its installer engine. |
| Microsoft Visual C++ runtime | [Microsoft Visual C++ redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist). Microsoft retains its applicable license terms. |

For the corresponding LottoLens source and build instructions, use the source archive attached to the matching GitHub release and see `packaging/README.md`.

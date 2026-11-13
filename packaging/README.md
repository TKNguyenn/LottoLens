# LottoLens V0.8.0 — Windows installer

Build output: `dist/LottoLens-Setup-0.8.0.exe`, Windows 10/11 x64. End users do not need Python. The installer supports Vietnamese/English, lets users select a writable destination, and offers launch/desktop-shortcut checkboxes on the completion page. A Start Menu app and uninstall entry are installed, plus the standard Windows Installed Apps entry.

## Layout and data

```
Chosen folder/
  LottoLens.exe
  LICENSE                     GNU GPLv3 text
  COPYRIGHT                   Copyright (C) 2026 TKNguyen; GPL-3.0-only
  third-party/                upstream license texts and corresponding-source links
  _internal/                  bundled Python, Qt, policy, icons, tutorial
  unins000.exe                Windows uninstaller
  unins000.dat
  data/                       created by the app, never shipped in setup
    history.sqlite3           history, reports, suggestions, scheduled-run records
    config.json               AI endpoint/model/key, only when explicitly saved
    ui_preferences.json
    theme.json
    window_geometry.bin
    policy-acceptance.txt
    onboarding-v1.txt
    source-cache/
```

All application user data stays under the chosen folder's `data` child. Windows shortcuts, uninstall registration and optional Task Scheduler registrations are OS integration records; they are removed by uninstall. Installation/uninstall logs and normal Windows temporary files are OS-managed.

The default location is `%LOCALAPPDATA%/Programs/LottoLens`. Pick another folder you can write to, such as `D:/Apps/LottoLens`. An unwritable destination is rejected. Running the source with `python main.py` still uses its existing paths; setup does not import or move the developer's database, preferences, API key or acceptance receipts. Existing source data can be backed up separately; no automatic migration is performed.

## In-app updates

LottoLens checks the [public GitHub release endpoint](https://api.github.com/repos/TKNguyenn/LottoLens/releases/latest) at startup after policy and onboarding, then every hour while open. The switch in Settings defaults to on and takes effect when saved. The sidebar button checks on demand even with the switch off.

Publish a stable GitHub Release tagged `vX.Y.Z` with the exact asset name `LottoLens-Setup-X.Y.Z.exe` and GitHub's SHA-256 asset digest. LottoLens prompts before downloading and checks the file size and SHA-256 before launching setup. Setup waits for the old app to exit, installs to the same directory and reopens LottoLens. It leaves the existing `data/` folder in place. Source runs and releases without a usable Windows installer offer the GitHub releases page.

## Uninstall

Use Windows Settings → Apps → LottoLens → Uninstall, the Start Menu uninstall entry, or `unins000.exe` in the chosen folder. Close the app first.

- **Remove app, keep data** (default): remove binaries, bundled resources, shortcuts, registration and this profile's daily tasks; leave `data` intact, including the API key if saved. Reinstall in the same location to reuse it. Save Settings again to register daily tasks after reinstall.
- **Remove app and all data**: confirm the permanent deletion of `data`, including saved API key, history, reports, suggestions and preferences. Unrelated files beside the app are preserved. A redirected/junction data root is rejected; nested junctions are not traversed.

Cleanup runs before executable removal and aborts uninstall if Windows refuses task cleanup or data deletion. Silent uninstall keeps data; `unins000.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /PURGEDATA=1` explicitly purges it.

## Rebuild

Use 64-bit Python 3.11 with `requirements.txt`, PyInstaller 6.22.3 and Inno Setup 6.7.4. Build dependencies are separate from app runtime dependencies. Download the compiler from the [Inno Setup download page](https://jrsoftware.org/isdl.php) and verify its Authenticode signature. The Vietnamese translation is vendored unchanged from [Inno's translation repository](https://raw.githubusercontent.com/jrsoftware/issrc/refs/heads/main/Files/Languages/Unofficial/Vietnamese.isl), including attribution.

```powershell
python -m pip install -r requirements.txt pyinstaller==6.22.3
python scripts/check_packaging.py
python -m pytest tests/ -q
python packaging/build.py --iscc "C:/path/to/Inno Setup 6/ISCC.exe"
```

The build reads `app.__version__` for EXE metadata, installer name and version; it writes a SHA-256 sidecar. `LottoLens.spec` allowlists the license/copyright notice, policy, icons and tutorial resources. The Inno script takes the EXE, `_internal` and root LICENSE/COPYRIGHT files, never `data` or the workspace config/database. Build logs are local in `build/`.

LottoLens is GPL-3.0-only, copyright 2026 TKNguyen. When distributing the setup, make the corresponding source and build instructions available under GPLv3 and preserve [third-party notices](THIRD_PARTY.md).

`LottoLens.exe --check-install PATH/report.json` is an explicit offline package diagnostic: open each page, both themes/languages and all tutorial images, verify installed paths and block socket connections. It creates an empty database in this copy's data folder. It does not accept policy, fetch history, call AI or register tasks. Use a disposable installation when running it.

The setup is unsigned. Windows may show an unknown-publisher/SmartScreen warning. A release signing certificate and validation on a clean Windows VM remain separate release work.

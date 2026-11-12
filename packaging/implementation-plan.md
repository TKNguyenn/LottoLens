# LottoLens V0.2.0 Windows setup

User request: selectable install directory containing app and data; final desktop-shortcut and launch checkboxes; uninstall with keep-data and purge-data choices.

## Design and scope

Use PyInstaller onedir plus Inno Setup (my implementation choice). Onefile alone cannot provide the requested install/uninstall workflow. MSI adds tooling and custom-action complexity without a requested benefit. Install per-user, no administrator requirement; default `{localappdata}/Programs/LottoLens`. Runtime files are in `_internal`, user files in `data` beside the EXE. An installed copy needs no Python.

Source runs retain existing paths. Frozen runs change only the location returned by storage.data_directory and settings.CONFIG_PATH; database schema, computation and networking stay unchanged. All resources are explicitly allowlisted. Never distribute developer config, keys, DB, receipts or schedules. No implicit migration of source/AppData data.

Daily tasks use LottoLens.exe --scheduled with the same existing CLI arguments and task identities. Uninstall removes only this installation's known tasks before removing executable files, aborts if cleanup fails, defaults to keeping data. Purge requires explicit selection/confirmation; silent uninstall keeps data unless /PURGEDATA=1. Purge is restricted to the real non-reparse `data` child, never a parent/install-root recursive deletion. Unrelated files survive. Installer prevents running-app replacement; uninstall maintenance mutex blocks new GUI/jobs.

## Execution and checks

- [x] Add assert-based `scripts/check_packaging.py`: source/frozen paths, frozen task executable/quoting, task cleanup failure/foreign-task isolation, safe purge (including junction), no GUI/network in scheduled mode. Missing paths import observed before implementation; green afterwards.
- [x] Add `app/paths.py`, `app/installation.py`, frozen-only path branches in settings/storage, frozen scheduler command, packaging entry point. Source behavior and API tests unchanged.
- [x] Add allowlisted PyInstaller spec, version metadata and build script. Compile with installed PyInstaller and signature-verified Inno compiler. Produced `dist/LottoLens-Setup-0.2.0.exe`.
- [x] Real disposable install, offline diagnostic, keep/reinstall/purge and task removal passed (`build/installer-smoke-a5x04ogx/result.json`). Native Vietnamese destination/completion pages and both Finish actions inspected. User stopped Computer Use with physical Escape during subsequent app inspection; interactive uninstall dialog was not inspected. A copy-only destination-label shortening was compiled afterwards; same bundled binaries, full install cycle not repeated on this final text change while the user's review app remained open.
- [x] Full protected suite 69 tests/23 subtests, packaging boundaries, daily scheduler, sync settings and geometry passed. Documentation and root handoff updated; Shared Brain captures durable state.

No code-signing certificate is available; deliver unsigned setup with checksum. Verify on this Windows host, not claim a clean VM or SmartScreen reputation test.

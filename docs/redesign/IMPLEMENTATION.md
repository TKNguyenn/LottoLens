# PySide6 redesign — implementation and validation

Implemented 2026-11-10 against `HANDOFF.md` and `vietlott-redesign.html`.

## Delivered

- `app/theme.py`: approved light/dark token dictionaries, QSS via `str.format`, palette, cached recolored SVG icons.
- `app/components/`: painted balls and wrapped/grouped result strips/delegates; badges, cards, callouts, empty states; heatmap/histogram, navigation, segmented control, theme switch and input helpers.
- `app/ui.py`: seven native pages, 236px rail, 56px topbar, 34px statusbar, 20/22px canvas spacing and bento grids. The application icon is `07-ticket-gold.ico`.
- `app/widgets.py`: native tables preserve `rowCount()` and `item(...).text()` while delegates paint results.
- `scripts/check_redesign.py`: offline assertions outside immutable `tests/`, including populated and empty games and layout checks.
- Theme is stored in `theme.json` beside the supplied config. Configuration schema and credentials storage are unchanged. Switching themes preserves the selected page, fields and generated results.

## Preserved contracts

All 33 pre-existing Desktop methods and the widget/state contract remain. SHA-256 comparison confirms all 22 baseline protected source/test files are unchanged. No dependency was added.

The user confirmed retaining incomplete backtest reports as required by the existing test. Cancelled history/AI results remain unsaved. An explicit UI worker guard also rejects `incomplete` history receipts before any write; a regression assertion was observed failing before that guard and passing after it.

The extra count/target/query/filter/verification controls are disabled during work and restored afterward. Network operations still start only from user actions, with no retries. Startup, cancellation, close behavior, streaming, snapshots and secret-free saved AI metadata are covered by the existing suite or offline assertions.

## Verification

```powershell
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' -m pytest tests/ -q
# 69 passed, 23 subtests passed
& 'C:/Users/kietj/AppData/Local/Programs/Python/Python311/python.exe' scripts/check_redesign.py
# Redesign OK
```

Checked all seven pages and all seven games, empty and populated, at 1000×700 and 1920×1080. Assertions cover horizontal overflow, wrapped-label heights, button clipping, theme persistence and state preservation, selected statistics windows, history filters, key reveal, source provenance, Vietnamese calendar dates, Max3D group heights, offline failure restoration, request count and incomplete history rejection. Windows' offscreen Qt plugin has no system fonts, so the check script loads installed Windows fonts for realistic geometry.

`main.py --db <temporary database>` opened and closed successfully using native Windows Qt. No live API/provider request was made. A separate read-only review reran both suites and found no outstanding actionable issue after fixes.

## Visual checks and intentional differences

The HTML was opened in a browser and all seven sidebar pages inspected in both themes. Qt captures are in `docs/redesign/reviews/native-ui/` (seven pages × two themes, plus seven captures at 1000×700). Captures use 12 historical rows embedded in the approved HTML, copied only to a temporary database; the suggestions capture uses the actual local uniform generator. These are preview data, not additions to the user's database.

- Native Windows titlebar preserves system resizing/snap/DPI behavior, as recommended by the handoff. Its dark appearance follows the chosen theme.
- History filters use a compact native dropdown; verification selects the single method actually accepted by the existing engine.
- The probability table retains the engine's exact fractions and percentages. Mockup-only export/aggregate features are not added. Keno is labeled as overlap probabilities, not a payout table.
- Explanation text and JSON report content remain available in their original text-browser API. No illustrative report or success state is inserted.
- Shadows/animations and browser-only effects are omitted. Physical multi-monitor and mixed-DPI interaction were not manually tested; live provider behavior was not probed.

Original UI backups and the protected-file hash manifest are in `.redesign-work/`. The supplied directory is not a Git repository; no commit or branch was created.

## Approved gradient and sidebar-header update — 2026-11-10

The current app applies `gradient/lottolens-gradient.html`'s light/dark gradients through existing QSS/QPainter components. The sidebar toggle now sits inside the brand header: expanded logo/name/button; compact centered panel glyph with logo/name hidden. Existing 236/68px widths, animation, keyboard/tooltips and state preservation remain. This supersedes the former topbar-toggle placement.

See `gradient/README.md` for tokens, validation and native screenshots in `gradient/native-expanded/` / `native-compact/`; root `implementation_handoff.md` section 11 records the change. No core/storage/network/tests or configuration schema changes. Browser-only shadow effects remain omitted; native gradient borders/highlights provide surface depth.

## Settings and live language update — 2026-11-10

Settings is appended at row 7, preserving all previous page indices and Desktop contracts. Vietnamese/English changes immediately from retained source copy, preserving inputs, generated selections, reports and raw AI text. Per-game counts control the next explicit history fetch, default 100/range 1–2000; they never prune saved draws. Save persists language/counts atomically in separate ui_preferences.json. About has the existing logo/name and one disabled GitHub button until a URL is provided.

See `settings/README.md`, its Windows screenshots, and root handoff section 13 for implementation, validation and limits. Original tests/core/storage/network/main.py remain unchanged.

## Configurable analysis window — 2026-11-10

User explicitly authorized history-window changes in generation.py, ai_generation.py and backtest.py; this supersedes the earlier core freeze only for those parts. One1–2000/default90 setting controls overview, statistical/AI generation and backtest warmup; Bayes prior strength stays90. Legacy preferences migrate to90; current batches retain their captured window metadata. Actual N reaches core calculations/AI context, labels and both generation/backtest menus. All other protected files remain unchanged (19 original hashes); no storage/transport/main.py/tests changes. See root handoff section14 and settings README for verification and AI input-size limit.

## Incremental retained history and daily schedules — 2026-11-11

The user's new request explicitly opens sources/storage for incremental synchronization and removal of active draws outside each game's configured limit. Proven retained windows stop source traversal at overlap; missing proof/increased limits refill the bounded range. Inserts, pruning and proof updates are atomic, including all ten Keno modes; saved snapshots/reports remain intact.

Settings now has per-game daily switches and HH:mm Vietnam times, off by default. Explicit Save installs native Windows Task Scheduler jobs that run with the GUI closed while the user is logged in and the computer is awake. Jobs claim a day before network, make one attempt, never invoke AI and do not catch up missed triggers. Registration and preference-file failures restore old schedules. Foreground DB polling preserves existing generated content and reports.

Original69 tests +23 subtests and new source/store/job/UI checks pass. A real temporary Windows task registered, ran pythonw with saved opt-in disabled, returned0, and was removed; live enabled fetches were mocked. Cumulative protected audit is17 unchanged plus5 authorized files. Details, limits and images are in root handoff16 and settings README.

## Max/Pro/Bingo18 odds and reference tickets — 2026-11-11

User approved `max-bingo/design.md`, including all 38 Bingo selections. Exact Fraction event math and typed generation now cover one-triple Max, ordered/identical-pair Pro, and all Bingo plays. Bingo plays are selections within the existing history mode. Max prize events are marginal and may overlap; union/no-win rows are computed separately. Current official July2026 draw rules verify replacement; formal participation rules and the official Pro demo corroborate pair/single-match predicates. Saved sources, hashes and page evidence are in `max-bingo/source-evidence.md`.

All four methods are connected: uniform, frequency, Bayes with prior90, and context-bound AI. Max input uses a complete fixed-width encoding of all20 results per draw, preserves groups/order/N and stays below the existing10k cap for the N90 fixtures. Oversize input is rejected before HTTP. No transport/storage/source/scheduler/main.py/tests changes in this feature; no automatic AI or retries. The UI synchronizes play/sample controls, preserves Pro order and leading zeros, caps distinct Bingo batches, translates immediately and locks inputs during workers.

Fresh original suite:69passed,23subtests. New exact-math/generation/desktop checks pass, including Windows native UI, save/reopen and mocked actual Desktop-to-AI context. Prior seeded set-game baseline and relevant old UI/settings checks pass. Independent final review found no actionable bugs. Audit: exactly8intended existing app files changed plus gameplay.py; cumulative original protected manifest14unchanged/8authorized exceptions. Twenty-six native screenshots use temporary data. No paid provider called. Exact repeated-result cash payouts, Max/Bingo backtest/simulation and new CLI play flags remain outside scope. See `max-bingo/README.md` and root handoff17.

## Shared table focus and footer clipping — 2026-11-11

All four ResultTable instances now use a shared TableItemDelegate that retains selected-row painting while removing the native per-cell focus frame. QTableWidget is removed from the generic red focus-border selector, so clicking does not change its viewport geometry. Full row selection remains visible with the theme's red_soft fill. Tab/Backtab preserves or creates a visible unhidden selection and scrolls it into view; arrows and multi-selection remain available.

ResultTable reserves trailing partial-row space below the viewport during geometry updates, preventing the footer from clipping numbered balls. A reentry guard avoids geometry recursion and scrolling refreshes the fit for variable-height grouped results. Final records remain reachable. Native/offscreen regression covers all four tables, both themes, two sizes, hidden rows, keyboard focus and grouped Max data; original69tests/23subtests and general UI checks pass. Images live in `reviews/table-interaction/`, technical details in root handoff20. No core/storage/network changes.

<p align="center"><img src="docs/redesign/assets/generated/07-ticket-gold.png" width="88" alt="LottoLens icon"></p>
<h1 align="center">LottoLens</h1>
<p align="center">Vietlott history, probability and statistics — in a desktop app.</p>
<p align="center"><a href="README.md">Tiếng Việt</a> · <strong>English</strong></p>
<p align="center">
  <img src="https://img.shields.io/badge/version-0.2.0-C81E33" alt="Version 0.2.0">
  <img src="https://img.shields.io/badge/platform-Windows_10%2F11-0078D4" alt="Windows 10 and 11">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB" alt="Python 3.11">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPLv3-blue" alt="GPLv3 license"></a>
</p>

![LottoLens overview in dark mode](docs/images/en-overview-dark.png)

**LottoLens** is a Python/PySide6 desktop app for browsing Vietlott history, exploring saved data, calculating theoretical probabilities and evaluating number-selection methods. Data is stored locally in SQLite. AI is optional.

> LottoLens does not promote betting, gambling or superstition. Past statistics, suggested numbers and AI output do not guarantee future predictions or improved winning chances. Read the [bilingual usage policy](POLICY.md).

*Screenshots show the actual app with synthetic data, not official draw results. Open an image to view it at full size.*

## Features

- **History with sources:** fetch Vietlott results, search by draw or number and open the original source. Updates are incremental when a verified history boundary exists.
- **Statistics and probabilities:** frequencies, heatmaps and theoretical odds, with a configurable recent-draw analysis window.
- **Number suggestions:** uniform, frequency, Bayesian and AI methods. Save suggestions with their method and history snapshot.
- **Local validation:** compare supported methods with random selection, using only history preceding each evaluated draw.
- **Per-game daily updates:** Vietnam-time schedules using Windows Task Scheduler, even while the app is closed.
- **Vietnamese and English:** immediate language switching, light/dark gradients, a collapsible sidebar, illustrated onboarding and game guides.
- **Optional AI:** HTTPS OpenAI-compatible endpoints, model fetching, manual model entry and streaming.

<details>
<summary>See light mode</summary>

![LottoLens overview in light mode](docs/images/en-overview-light.png)

</details>

## Getting started

### Run from source

Tested with **Windows x64, Python 3.11 and PySide6 6.11.2**.

```powershell
git clone https://github.com/TKNguyenn/LottoLens.git
cd LottoLens
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

On first launch, the main window appears behind the policy dialog. Check **I have read** and **I accept** separately to continue to the illustrated tutorial. Reopen it through **Help** in the top bar; the policy is available under **Settings → About**.

### Windows installer

Check [Releases](https://github.com/TKNguyenn/LottoLens/releases) for published builds. If no setup asset is attached, run from source or [build the installer](packaging/README.md).

The installer lets you choose a folder for the app and its data; Python is not required on the destination computer. The final page offers desktop-shortcut and launch checkboxes. Uninstall can **keep user data** or **remove all user data**; both remove this installation's scheduled tasks. Setup is currently unsigned, so Windows may show an unknown-publisher warning.

## How to use it

### 1. Choose a game and fetch history

Select a game in the top bar, then click **Update history**. The initial update downloads the configured range, 100 draws by default. Later updates fetch new results until the verified boundary; increasing the limit or revalidating data may require fetching the full range again.

After a valid update, the app retains up to the selected count and removes older draws outside that range. Saved suggestions, reports and snapshots are preserved. Failed, cancelled or incomplete downloads leave history unchanged. **Import CSV** supports set-based games using the [format below](#csv-and-command-line).

![History table with result balls](docs/images/en-history-light.png)

### 2. Explore statistics and theoretical odds

Use **Statistics** for frequencies and heatmaps. Use **Odds** for theoretical probabilities by game, ticket or play type. **Game guide** explains selection rules, draw mechanics and winning conditions, with official source links.

**Observed frequency is not a forecast probability.** Under a fair-draw assumption, all valid combinations of the same ticket type have the same theoretical odds.

![Statistics and heatmap using sample data](docs/images/en-stats-dark.png)

### 3. Generate suggestions and validate methods

In **Number suggestions**, choose a method and count, then generate. Uniform selection works without saved history; frequency, Bayesian and AI methods need the configured analysis window. Enter an **Intended draw** only when saving for later comparison.

In **Validation**, select a local method to compare with random selection. If the analysis window is 100 and only 100 draws are saved, validation uses at most 99 as input, reserves a draw for evaluation and displays a note. At least two draws are required. AI is not used for batch backtesting.

### 4. Configure history, analysis and daily updates

| Setting | Default | Purpose |
| --- | --- | --- |
| Retained draws, per game | 100 | History range to keep after a valid update |
| Recent draws used for analysis | 90 | Input for overview, frequency/Bayesian/AI methods and validation warm-up |

In **Settings**, enable **Automatic**, choose each game's time and click **Save settings**. Schedules use **UTC+7** and run while the computer is on and the Windows account is signed in, even if the app is closed. All schedules are off by default. Missed times are not caught up; a failed game is not retried automatically that day. Use **Update history** for a manual attempt. Keno updates share results across all ten pick modes.

![Language, analysis window and automatic-update settings](docs/images/en-settings-light.png)

### 5. Configure AI — optional

Local features do not need an API key. To use AI:

1. Open **AI & settings** and enter an HTTPS Base URL, defaulting to `https://api.openai.com/v1`.
2. Enter your provider's API key, click **Fetch models** and choose a model, or enter its ID manually.
3. Click **Test model** to check it, or **Save configuration** to store the configuration locally.
4. Explicitly request a web search or use **AI history analysis** when needed.

The app selects Responses → Chat Completions → Completions, switching only on a 404/405 that identifies an unsupported endpoint. Key/model/rate/network errors, ambiguous errors and responses that have already started stop the operation. Discovery tries at most three paths. AI is never called automatically at startup. Web search and High reasoning require provider/model support; Legacy Completions supports neither feature.

**AI may incur charges and produce incorrect content.** History analysis sends required history to your selected provider. If saved, the API key is stored as plaintext in `config.json`; keep it out of Git. AI output is never imported as official draw history.

![AI configuration and model fetching](docs/images/en-ai-dark.png)

## Supported games

| Game | Probabilities and suggestions | Prize-tier backtesting |
| --- | --- | --- |
| Mega 6/45 | Supported | Supported |
| Power 6/55 | Supported, separate bonus number | Supported |
| Lotto 5/35 | Supported, separate special number | Supported |
| Keno pick 1–10 | Match-count distribution and suggestions | Not enabled |
| Max 3D | Single `000–999` ticket, event probabilities | Not enabled |
| Max 3D Pro | Ordered pair of triples, repeated pairs allowed | Not enabled |
| Bingo18 | All 38 choices within the modeled play groups | Not enabled |

Keno does not yet provide complete payout odds. Max/Bingo simulation, backtesting and full payout/EV calculations are not enabled. System-entry variants and Max 3D+ need separate engines. Rules are observed models, not certified historical coverage for every past draw. See the [support matrix](docs/game_support_matrix.md) and [source audit](docs/source_audit.md) (Vietnamese).

## Where is data stored?

| Runtime | History and reports | Configuration |
| --- | --- | --- |
| Installer / EXE | `data/history.sqlite3` beside the EXE | The same `data` folder |
| Python source | `%LOCALAPPDATA%/VietlottDesktop/history.sqlite3` | Project root |

`ui_preferences.json`, `theme.json` and `window_geometry.bin` are separate from AI configuration. The EXE stores policy/tutorial receipts and source cache under `data`; source runs store them beside the database. There is no cloud sync or automatic source-to-installer migration. Close the app before backing up the database and configuration; for an installed copy, back up the entire `data` folder.

## CSV and command line

CSV example for set-based games:

```csv
draw_id,draw_date,main,special
01586,2026-11-08,01 02 14 20 23 36,
```

Examples in a Python environment with dependencies installed:

```powershell
python main.py self-check
python main.py sync --game mega --limit 100
python main.py history --game mega
python main.py odds --game power
python main.py odds --game keno --mode pick8
python main.py import-csv --game mega "history.csv"
```

The CLI has a narrower scope: it does not expose every Bingo18 ticket choice or replace all GUI controls. Run `python main.py --help`.

## Development and checks

```powershell
python -m pip install pytest pytest-subtests
python -m pytest tests/ -q
python scripts/check_packaging.py
```

AI tests use mocked responses and do not call a real provider. Windows setup uses PyInstaller and Inno Setup; see the [build instructions](packaging/README.md). Refresh README images with `docs/images/capture.py`; it uses synthetic data in a temporary directory and blocks networking.

## License

**Copyright © 2026 TKNguyen.** **GNU GPLv3 only (`GPL-3.0-only`)** — [LICENSE](LICENSE), [COPYRIGHT](COPYRIGHT). Binary and modified distributions must comply with GPLv3, including corresponding-source requirements. Third-party components retain their own licenses. [POLICY.md](POLICY.md) describes app purpose/limitations without adding restrictions to GPL rights.

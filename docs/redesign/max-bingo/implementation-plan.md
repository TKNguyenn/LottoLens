# Max/Bingo Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for implementation; independent source research and final read-only review may run separately. Steps use checkboxes for tracking.

**Goal:** Exact theoretical odds and four reference-ticket methods for Max 3D, Pro and all 38 Bingo18 selections in the existing desktop app.

**Architecture:** Keep Ticket/Draw/mode/storage contracts. Add `app/gameplay.py` for typed selections, finite Bingo choices and exact event math; existing domain/probability/generation/AI/UI call it. Preserve the set-game code path and default results.

**Tech Stack:** Python 3.11, standard library Fraction/Counter/itertools, existing PySide6.

**Spec:** `docs/redesign/max-bingo/design.md`, approved 2026-11-11.

## Global constraints

- No new dependencies, no tests/ or main.py changes, no AI transport/storage/source/scheduler changes.
- No automatic AI/retry, incomplete persistence or secret metadata; keep input limit10,000 and N setting.
- Preserve history identity/version, Desktop API, theme/language behavior and prior set-game results.
- Ruling: execute in current workspace (no Git repository); snapshots/hashes provide baseline. User approved implementation; no repeat approval gate for implementation mechanics.

## Review focus

Wrong AI play context; Pro order/trailing zeros; overlapping odds and identical pairs; finite Bingo capacity; language/worker/new controls. Each receives a regression below.

## Task 1 — rules and exact math

Files: new gameplay.py, scripts/check_max_bingo_core.py; modify domain.py, rules.py, probability.py.
Interfaces: `bingo_choices(play_context=None)` yields selections `{play: str, main: list}`; contexts single/double/triple/any_triple/sum/size (default single). `ticket_capacity(rule, play_context=None)`, `sample_selections(rule, play_context=None)`, `bingo_outcomes(selections, result)` returns named event booleans; `game_probabilities(rule, selections)` Fraction mapping. Max selections keep existing main strings; Pro order retained.
- [x] Write/run RED: 38 choices, strict play/values, 216 independent outcomes; Max/Pro exact union/order/identical pairs and reduced-domain enumeration.
- [x] Verify decisive primary-source draw/predicate evidence before enabling math_ready. Record source and remaining assumptions.
- [x] Implement exact formulas/helper validation; wire probability dispatch and ready flags only when justified; run original suite.

## Task 2 — generation and AI

Files: generation.py, ai_generation.py; scripts/check_max_bingo_generation.py.
Interfaces: optional final play_context=None on profile/generate/explain_ticket/request/parse/AI APIs. Profile retains common keys; new candidate keys are triple strings or Bingo main choice. Parser binds requested context. Existing set-game calls unchanged.
- [x] RED: each method produces valid/unique typed tickets, Pro order, zero prefixes, finite capacity, N/metadata; AI context rejects mismatched/extra fields, duplicate/error/cancel no retry.
- [x] Add new-kind branch preserving old path. Bayes prior90; triple observation unit per-draw occurrences, Bingo per-draw win events. Uniform uses equal candidate weights.
- [x] Compact Max history preserves all groups/order/N and hashes; reject >10,000 before HTTP. Mock enabled AI paths and run original suite/default-hash checks.

## Task 3 — desktop and verification

Files: ui.py, components/__init__.py, i18n.py; scripts/check_max_bingo_ui.py; docs in this folder + handoff/support matrix.
- [x] RED: new controls/context/sample odds, Bingo 38 choices, generation/save/reopen, dynamic limits, worker locks, VI/EN/two themes/small layout.
- [x] Add synchronized Bingo play/choice and Max sample inputs on Odds and Suggestions; shared context, no history mode changes. Format typed choices and Pro order; keep ball rendering.
- [x] Distinguish marginal vs union odds; show correct sample-based descriptions and preserve prior generated provenance when merely viewing another sample.
- [x] Run original suite, new checks, relevant old UI checks; inspect native captures from temporary DB, no paid API or real history mutation.
- [x] Independent final review, fix actionable findings, audit frozen files, update design/handoff/support docs with actual verification and limits.

## Progress ledger

- Setup: design approved, current files read, no product edits yet. Independent official-source research started.
- Task1 complete: RED Bingo rejected; GREEN38choices/216outcomes/reduced-domain brute force; added malformed Max ticket regression (TypeError→ValueError). July2026 PDFs and official Pro demo settle replacement/inclusive events. Ruling: exact closed formulas instead of DP because inclusion-exclusion/binomial fully describe required events.
- Task2 complete: RED unexpected play_context; GREEN local methods and context-bound AI. N90 Max compact request under10k; N200 oversize rejected before send. Set-game seeded baseline parity unchanged. Optional context is a whitelist string; defaultNone maps to Bingo single.
- Task3 complete: RED missing ticket_controls; GREEN Desktop local+AI mock, finite capacities, save/reopen, worker locks, preserved generated provenance, native Windows VI/EN/light/dark. Ruling: explicit Any triple combo entry rather than nested subselector keeps all38choices while making its one-ticket limit clear. Native26captures inspected; fixed hidden-column spacing, small explanatory caption and enough height for all Pro odds rows.
- Final verification:69passed/23subtests; new core/generation/UI scripts passed (UI offscreen and Windows). Old general redesign, preferences, analysis core/window, backtest window, sync settings and i18n checks passed. Hash audit exactly8intended existing app files changed plus gameplay.py; tests/main/storage/source/scheduler/AI transport unchanged this task.
- Final fresh-context reviewer verdict: Ship, no actionable bugs. Provider mocked; no paid AI/user data mutations. Event probabilities do not establish repeated-result payout amounts, historical cash/EV, backtest or simulation for these games. No new dependencies or Git commits (not a repository).

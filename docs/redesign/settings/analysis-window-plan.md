# Configurable analysis history — implementation plan

User request: choose the recent draw count used for calculation instead of fixed90. Explicit user exception authorizes changing only history-window handling in app/generation.py, app/ai_generation.py and app/backtest.py (otherwise protected by HANDOFF2.4). All other core/storage/network/tests/main.py stay immutable.

Design: one analysis-window setting, default90/range1–2000, separate from per-game download counts. Applies immediately to overview hot frequencies/expectation, Bayesian/frequency generation, AI context and backtest warmup. Existing statistics page keeps its separate30/all selectors and replaces its90 preset with configured N. Save persists analysis_window in ui_preferences.json; legacy two-key preferences load with default90.

APIs: generation_profile/explain_ticket/generate accept optional history_window=90; build_generation_request/generate_with_ai accept same additive argument; run_backtest config accepts history_window default90. Prior strength stays90, so Bayes formula is (count+90*fair)/(N+90). Default seeded generation and existing callers retain behavior. Keep legacy algorithm IDs, record history_window in metadata/manifest to distinguish parameters. AI instructions/context/metadata use actual selected N, request still only on explicit action, one attempt/no web. No store schema or CLI changes.

- [x] Add core/UI assert regression outside tests/, observe missing-window failure.
- [x] Implement optional core window plus validation, cutoff/AI request/manifest provenance and warmup; keep90 backward compatibility.
- [x] Add UI setting, preferences migration, dynamic copy VI/EN, overview/statistics/method wiring, worker locks and persisted generation metadata.
- [x] Verify real30/120 sample counts and last-draw selection, future-target isolation, insufficient history/no HTTP, default tests, live language and settings layouts; independent review and native screenshots.
- [x] Update root implementation_handoff.md, settings README and protected-file exception evidence.

Verification: original69 tests +23 subtests pass; analysis core/UI, settings, general UI, sidebar/gradient and i18n checks pass. Native Windows N120 captures and mocked-AI UI regression pass. Review corrected backtest option/minimum copy and confirms Ship. Protected audit shows exactly3 authorized changes and19 unchanged files; original hash manifest retained. See root handoff14 for details and limits.

Non-goals: change prior tuning, claim improved odds, auto-download missing data, retry requests, prune history, change database schema, add CLI flags, change AI reasoning/model/protocol. Backtest AI remains disabled.

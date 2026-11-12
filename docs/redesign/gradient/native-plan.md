# LottoLens Gradient — native implementation

> Execution: superpowers:executing-plans, inline. User approved the HTML gradient and requested the Piaz Switch sidebar header on 2026-11-10.

**Goal:** Apply the approved gradient study to both native Qt themes and move the sidebar toggle into the brand header.

**Spec:** `lottolens-gradient.html`, `README.md`, user-provided expanded/collapsed Piaz Switch screenshots. Native Qt only; retain 236/68px widths and existing animation, navigation, tooltips, keyboard activation and theme persistence.

**Architecture:** Extend the existing two token dictionaries and QSS using `str.format`; reuse QPainter in current components for gradients. Change only the presentation shell in Desktop. The collapsed header hides logo/text and centers the same panel button; the expanded header shows logo/name/button. No new setting, dependency, network behavior or storage changes.

**Files:** `app/theme.py`, `app/components/__init__.py`, `app/ui.py`; assert-based checks in `scripts/check_gradient.py` and existing `scripts/check_sidebar.py`; captures/docs under this gradient folder; root `implementation_handoff.md`.

**Review focus:** Native painting really produces gradients; dark CTA uses dark text with sufficient contrast; sidebar header never clips or shifts the rail's minimum width; rapid animation reversal/state retained; startup and theme/nav changes make no network calls.

- [x] Add focused rendered-gradient/sidebar-header checks; run and observe failure against current UI.
- [x] Add gradient tokens/QSS and update painted balls, nav, charts, icons and heatmap text contrast. Mark latest-result card as hero. Run focused checks and full existing suite.
- [x] Move toggle into sidebar header, hide logo/text when compact, use a plain panel glyph. Run sidebar check, general UI check and full suite.
- [x] Capture both themes/header states and all seven pages, inspect key images, native Windows smoke, protected-file hashes, independent review.
- [x] Update gradient README, central design index, implementation notes and root handoff with results and remaining limits.

Verification: pytest 69 passed + 23 subtests; gradient/sidebar/redesign checks passed; Windows main.py event-loop smoke passed; 22 protected hashes unchanged. Independent reviewer confirmed the light heatmap ink fix and reran the rendered regression; final verdict Ship with no remaining actionable findings. Details and limits are in README.md and root handoff section 11.

No Git repository is present; no commit/worktree steps apply. Avoid heavyweight per-card shadow effects; native gradient borders/highlights provide depth without offscreen composition effects.

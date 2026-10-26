# Flow 2 — Mazor Ship Flow Map

A generated page that explains the delivery flow of [`Mozar-Team/factory-that-builds-itself`](https://github.com/Mozar-Team/factory-that-builds-itself) in plain language. It lives outside the game repository so the game's git history stays clean; the game repository is only read.

It has five tabs:

| Tab | What it shows | Source |
| --- | --- | --- |
| Current flow | The lean flow in force since 2026-10-21 (contract schema 6): the chain of gates, ELEVATED extras, what changed from V3, live check of the first task through it (#116) | `.codex/workflow-policy.toml` on `main` + `V4_*` in `io_map.py` (steps follow `docs/workflow/SHIP_WORKFLOW.md`) |
| V2/V3 map | Archived map of the STANDARD/ELEVATED routes and the automation, built from the rules at `3370cfc` | policy at `ARCHIVE_REF` |
| V3 status | Snapshot of the event-driven automation on 2026-10-15 and the merged retreat (#115) | `SNAPSHOT_V3` in `io_map.py`, every row linked |
| Governance | The flow as an AI-delivery governance pattern; each control's policy key is checked against the current policy | `CONTROLS`, `GAPS` in `io_map.py` |
| History | Eras from August to today, policy size and process-code size per era, searchable log of process-only changes | `git log`, `ERAS` in `io_map.py` |

The page has no authority. If it disagrees with `.codex/workflow-policy.toml`, the policy wins.

## Build

```bash
python build.py --repo PATH_TO/factory-that-builds-itself --ref origin/main --standalone
```

Writes `docs/index.html`. To publish it with GitHub Pages: Settings → Pages → Deploy from a branch → `main` / `docs`.

- Needs Python 3.11+ and the full git history (`git fetch --unshallow` in a shallow clone).
- Set `GITHUB_TOKEN` to read the live canary status from GitHub Actions; without it the page says the status could not be read.
- Open `docs/index.html` in a browser. GitHub does not render HTML files in the repository view.

## What updates by itself and what does not

| Updates on every build | Written by hand |
| --- | --- |
| Route steps and their order, numbers (repair limit, parallel writers), categories, reviewers, protected paths, canary status, process change log, policy size per era | Step descriptions, the V3 status snapshot, governance controls, era names and lessons |

A new step, category or policy section that `io_map.py` does not describe appears on the page with a warning.

## Status on 2026-10-26 (summary)

- **Retreat merged.** [#115](https://github.com/Mozar-Team/factory-that-builds-itself/pull/115) FLOW-RECOVERY-001 merged on 2026-10-21: policy 357 → 81 lines, production workflow Python 6,867 → 1,456 lines, event controller, runner and paired admission removed.
- **Lean flow in use.** [#116](https://github.com/Mozar-Team/factory-that-builds-itself/pull/116) HUD-SPRITE-001: ACCEPT 2026-10-23, PENDING VERIFICATION 2026-10-24, Product Owner decisions 2026-10-26, waiting for Independent QC.

Details and links are on the Current flow and V3 status tabs.

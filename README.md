# Flow 2 — Mazor Ship Flow Map

A generated page that explains the delivery flow of [`Mozar-Team/factory-that-builds-itself`](https://github.com/Mozar-Team/factory-that-builds-itself) in plain language. It lives outside the game repository so the game's git history stays clean; the game repository is only read.
It has four tabs:

| Tab | What it shows | Source |
| --- | --- | --- |
| Flow map | The STANDARD and ELEVATED routes, every step with what it gets, gives and when it stops; the automation; the QC loop; routing rules | `.codex/workflow-policy.toml` (read at build time) + `io_map.py` (words only) |
| V3 status | Snapshot of the event-driven automation on 2026-10-15: what works, what is broken, why nothing moves | `SNAPSHOT_V3` in `io_map.py`; every row links its PR comment or run |
| Governance | The flow read as a general AI-delivery governance pattern: controls, policy keys, gaps | `CONTROLS` and `GAPS` in `io_map.py`; framework mapping is the author's reading, not a certification |
| History | Eras of the flow from August to October, policy size per era, and a searchable log of process-only changes | `git log` over the protected process paths, `ERAS` in `io_map.py` |

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

## V3 status on 2026-10-15 (summary)

The automation runs, but no task can move through it.

- Game task #113 (HUD-SPRITE-001) waits for #114, the fix that pins model and effort when native sessions resume.
- #114 (FLOW-NATIVE-ROLE-PIN-001) had two writer attempts, both blocked before any change: first by GitHub HTTP 404/401, then by a conflict between the runner's fixed writer prompt ("Do not … alter policy", `scripts/workflow/local_runner.py:1668`) and a contract that requires a policy edit.
- #110 (FLOW-AUTO-CONTINUITY-001) used its two repairs and is frozen.
- Last workflow canary pass: 2026-10-11 on `4d834d4`; `main` is six merges ahead.

Details and links are on the V3 status tab.

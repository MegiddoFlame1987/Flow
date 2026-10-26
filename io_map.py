"""Human-readable layer of the flow map.

build.py reads steps, order and values from .codex/workflow-policy.toml and history
from git. This file only adds words. Sources: docs/workflow/SHIP_WORKFLOW.md,
docs/workflow/FLOW_AUTO_RUNNER.md, and the PR comments linked in SNAPSHOT_V3.
A step, category or policy section missing here shows up on the page with a warning.
"""

ACTORS = {
    "po": "You (Product Owner)",
    "orch": "Orchestrator",
    "rev": "Reviewers",
    "arch": "Architect",
    "writer": "Writer",
    "ci": "Automated checks",
    "qc": "Independent QC",
}

STEPS = {
    "orchestrator": {
        "title": "Orchestrator takes the task",
        "actor": "orch", "src": "po",
        "plain": "Reads your brief and confirms the task is large or risky, so it takes the ELEVATED route.",
        "inputs": ["Your brief: what to change and what the player should see", "Task status from the task list", "Relevant parts of the game documents"],
        "outputs": ["Route decision", "Reviewers to ask"],
        "gate": "If the brief is unclear, it asks you and waits.",
        "tech": ["Brief starts with `SHIP:`", "Categories: `routing.forced_elevated_categories`", "Sources: `docs/gdd.md`, `docs/LORE_BIBLE.md`, `docs/WORLD_MECHANICS.md`"],
    },
    "relevant-reviewers": {
        "title": "Reviewers assess the idea",
        "actor": "rev", "src": "orch",
        "plain": "Specialists for gameplay, story, world physics and architecture review the idea. They only read and change nothing.",
        "inputs": ["Brief", "Which areas the change touches"],
        "outputs": ["Notes for the plan"],
        "gate": "",
        "tech": ["Mapping: `reviewer_mapping`", "Roles: `.codex/agents/*.toml`"],
    },
    "required-reviewers": {
        "title": "Required reviewers assess the idea",
        "actor": "rev", "src": "orch",
        "plain": "For a large change the review is mandatory. Reviewers only read.",
        "inputs": ["Brief", "List of risk areas"],
        "outputs": ["Notes for the plan"],
        "gate": "Without a required reviewer the task stops.",
        "tech": ["Mapping: `reviewer_mapping`", "Missing reviewer = BLOCKED"],
    },
    "task-contract-plan": {
        "title": "The task contract is written",
        "actor": "orch", "src": "rev",
        "plain": "The pull request description becomes a contract: which files may change, the plan, how it will be checked and what decision the player gains.",
        "inputs": ["Brief", "Reviewer notes", "Current state of the game"],
        "outputs": ["Draft PR with the contract"],
        "gate": "Waits for your approval.",
        "tech": ["Contract schema 5 between `<!-- FLOW-V2-CONTRACT:START -->` and `END`", "Fields: allowed paths, plan, tests, `## Player decision`, product_test_matrix", "Base = exact `main` SHA"],
    },
    "conditional-architect-specification-in-pr-contract": {
        "title": "Architect writes a specification (when needed)",
        "actor": "arch", "src": "orch",
        "plain": "Only for changes to code structure, saves or public interfaces. The Architect describes how to build it.",
        "inputs": ["Draft contract"],
        "outputs": ["Specification inside the contract"],
        "gate": "Skipped when only game documentation changes.",
        "tech": ["Categories: `routing.architect_required_categories`", "Exception: `canonical_docs_only`"],
    },
    "product-owner-accept-with-writer": {
        "title": "You approve (ACCEPT)",
        "actor": "po", "src": "orch",
        "plain": "You accept the plan and pick who writes: Codex or Claude Code. Only from this moment may the repository change.",
        "inputs": ["Task contract"],
        "outputs": ["Your ACCEPT comment"],
        "gate": "Without your approval nobody writes anything.",
        "tech": ["ACCEPT names: route, orchestrator, writer + session, allowed paths, plan", "Automation requires a contract code: `automation.accept_requires_contract_code`"],
    },
    "start-preflight": {
        "title": "Start check",
        "actor": "ci", "src": "po",
        "plain": "A script checks that everything matches and that the writer has a free slot. At most two writers work at once.",
        "inputs": ["Pull request", "Slot grant (lease)"],
        "outputs": ["Go or stop"],
        "gate": "No go, no writing.",
        "tech": ["`python scripts/workflow/preflight.py start --pr N --writer P --writer-session S`", "Lease from `.github/workflows/writer-admission.yml`"],
    },
    "selected-writer-orchestrator": {
        "title": "Writer builds the change",
        "actor": "writer", "src": "ci",
        "plain": "In small tasks one session writes the code and runs the task. It makes the smallest change in the plan, tests it and leaves evidence.",
        "inputs": ["Your approval", "Contract and the list of files it may change"],
        "outputs": ["Finished change", "Test results", "Evidence comment"],
        "gate": "Stops and waits for QC.",
        "tech": ["Status: PENDING VERIFICATION + SHA", "Godot headless tests", "Writer no. 2 waits for refresh (pending refresh)"],
    },
    "selected-writer": {
        "title": "Writer builds the change",
        "actor": "writer", "src": "ci",
        "plain": "A separate writer session makes the change from the plan and specification, tests it and leaves evidence.",
        "inputs": ["Your approval", "Contract, specification and file list"],
        "outputs": ["Finished change", "Test results", "Evidence comment"],
        "gate": "Stops and waits for QC.",
        "tech": ["Status: PENDING VERIFICATION + SHA", "Godot headless tests", "Writer no. 2 waits for refresh (pending refresh)"],
    },
    "validation": {
        "title": "Automated checks",
        "actor": "ci", "src": "writer",
        "plain": "GitHub validates the configuration and runs the game without a screen to catch errors.",
        "inputs": ["Latest version of the change"],
        "outputs": ["Green or red checks"],
        "gate": "Red checks must be fixed by the writer.",
        "tech": ["Checks: `validate`, `Godot 4.7.1 headless smoke check`", "Logs as CI artifacts"],
    },
    "independent-qc-comment": {
        "title": "Independent QC",
        "actor": "qc", "src": "orch",
        "plain": "A new, separate session trusts nothing it is told. It checks the change and the tests itself and gives a verdict: PASS, FAIL or BLOCKED.",
        "inputs": ["The change to verify"],
        "outputs": ["Verdict comment", "Wake-up signal to the orchestrator"],
        "gate": "PASS moves on. FAIL or BLOCKED stops and sends you one message.",
        "tech": ["Start: `/qc-comment PR N notify <session>`", "Comment has 8 keys (see the QC loop)", "Wake-up: `send_message`"],
    },
    "conditional-closeout": {
        "title": "Result is recorded",
        "actor": "orch", "src": "qc",
        "plain": "After PASS one commit writes the result into the task list.",
        "inputs": ["PASS verdict"],
        "outputs": ["Task list entry"],
        "gate": "Only touches the task list (and the findings report on ELEVATED).",
        "tech": ["Paths: `TASKS.md`, `docs/verification/{task_id}-findings.md`"],
    },
    "final-preflight": {
        "title": "Final check and playtest package",
        "actor": "ci", "src": "orch",
        "plain": "A script confirms everything is green and ready to merge. You get short instructions on what to click in the game.",
        "inputs": ["QC verdict", "Check results"],
        "outputs": ["Go", "Playtest package: what to click, what should happen, what changes, what stays open"],
        "gate": "Checks must be green on the latest version.",
        "tech": ["`python scripts/workflow/preflight.py final --pr N --qc-comment-url URL ...`"],
    },
    "product-owner-playtest-manual-merge": {
        "title": "You playtest and merge",
        "actor": "po", "src": "ci",
        "plain": "You play by the package, confirm with a comment and merge the change yourself. Only then does it enter the game.",
        "inputs": ["Playtest package"],
        "outputs": ["Your playtest confirmation", "Merge into the main version"],
        "gate": "Agents never merge.",
        "tech": ["Check `po-playtest` reads your comment through the GitHub API", "A new code or base version invalidates the confirmation"],
    },
}

STANDARD_MERGED_ACTORS = {"orch": "writer"}

LANE_INTRO = {
    "STANDARD": "Ordinary, small tasks. One AI session writes and runs the task, a second, separate one checks it.",
    "ELEVATED": "Large or risky tasks: architecture, canon, economy, saves, gameplay numbers. Running, writing and checking are three separate sessions.",
}

CATEGORY_LABELS = {
    "architecture": "code structure", "canon": "story canon", "gdd": "game design document",
    "core_loop": "core game loop", "power_rules": "power rules", "survival": "survival",
    "economy": "economy", "broad_progression": "broad progression changes", "persistence": "saved state",
    "save_or_schema_migration": "save migration", "quantum_detector_prediction_endgame": "detector endgame",
    "iro_core": "IRO core", "public_api": "public interfaces", "broad_refactor": "large refactor",
    "multiple_systems": "several systems at once", "unclear_blast_radius": "unclear impact",
    "numerical_gameplay_values": "gameplay numbers", "bounded_balance_data": "tuning numbers within agreed ranges",
}

REVIEWER_LABELS = {
    "game-design-reviewer": "gameplay reviewer", "canon-reviewer": "canon reviewer",
    "world-systems-reviewer": "world and physics reviewer", "architecture-reviewer": "architecture reviewer",
}

NOTIFY_LABELS = {
    "READY_TO_ACCEPT": "a contract waits for your approval",
    "READY_TO_PLAYTEST": "a change waits for your playtest",
    "READY_TO_MERGE": "everything is ready to merge",
    "NEEDS_PO": "something is stuck and needs your decision",
}

STOP_LABELS = {
    "NO_CAPACITY": "no free writer",
    "NO_ELIGIBLE_TASK": "no task you marked as ready",
    "MISSING_PRODUCT_DECISION": "a product decision of yours is missing",
}

KNOWN_SECTIONS = {
    "session_usage", "permissions", "identity", "routing", "reviewer_mapping", "lanes",
    "architect_exception", "claude_read_only_wrappers", "repair", "evidence", "preflight",
    "repository_sources", "products", "admission", "bounded_balance", "automation",
    "playtest", "replenishment",
}

AREAS = [(".codex/", "agent rules"), ("AGENTS.md", "agent rules"), ("CLAUDE.md", "agent rules"),
         (".claude/", "Claude tooling"), (".github/", "GitHub automation"), ("docs/workflow/", "process docs"),
         ("scripts/workflow/", "process scripts")]

# --- History: eras are the writer's reading of the git log; counts are computed by build.py.
ERAS = [
    {"from": "2026-08-17", "to": "2026-08-31", "name": "Foundations",
     "what": "Written agent rules, verification records committed with the change, a sequential batch loop and the first Godot headless CI gate.",
     "lesson": "Rules existed only as text. Nothing enforced them."},
    {"from": "2026-09-01", "to": "2026-09-26", "name": "Flow V2 pilot",
     "what": "Workflow automation v1, repository-first governance, then the Flow V2 pilot: task contract in the PR, start and final preflight scripts, Product Owner ACCEPT before writing.",
     "lesson": "Rules became machine-checked. The first QC FAIL and repair cycle happened on the governance work itself."},
    {"from": "2026-09-27", "to": "2026-10-07", "name": "Simplify and harden",
     "what": "FLOW-V3-LITE-001 simplified delivery, the tracker was compacted, products collapsed to one (`main`), repair rules and resume rules were written down.",
     "lesson": "After this lighter V3 attempt the rules still call the flow V2; the name V3 returned with the event-driven automation."},
    {"from": "2026-10-08", "to": "2026-10-09", "name": "Local runner",
     "what": "A bounded local runner performs one transition at a time with crash-safe intent records, ntfy notifications, a live canary requirement, then two-slot parallel admission with server-issued receipts and per-role effort limits.",
     "lesson": "Automation was allowed only with proof that it ran live (canary), not only in tests."},
    {"from": "2026-10-10", "to": "2026-10-11", "name": "Event-driven Flow (V3)",
     "what": "Cloud sessions, @claude mentions, QC waking the orchestrator, then FLOW-AUTO-EVENT-001: GitHub events wake a self-hosted Windows runner that prepares, writes, verifies and records tasks. Missing product decisions are recommended, never invented.",
     "lesson": "The workflow canary passed on 2026-10-11 after failed attempts on 10 Oct."},
    {"from": "2026-10-12", "to": "2026-10-14", "name": "Stall",
     "what": "Continuity repair #110 used both repairs and was frozen. HUD work #113 is blocked because resumed native sessions do not keep their model and effort. The adapter fix #114 failed twice before writing anything.",
     "lesson": "Green workflow runs did not mean tasks moved. See the V3 status tab."},
    {"from": "2026-10-15", "to": "2026-10-21", "name": "Retreat",
     "what": "FLOW-RECOVERY-001 (#115), accepted 15 Oct and merged 21 Oct, removed the event controller, the local runner, paired admission and their tests, and kept contract, ACCEPT, one writer, independent QC, preflight and the playtest gate.",
     "lesson": "The first flow change that made the process smaller: production workflow Python went from 6,867 to 1,456 lines."},
    {"from": "2026-10-22", "to": "2026-10-31", "name": "Lean flow (V4)",
     "what": "Schema 6: brief, start, ACCEPT, one writer, independent QC, playtest receipt, manual merge. HUD-SPRITE-001 (#116) is the first task through it.",
     "lesson": "Too early to judge: one task, not yet through QC."},
]

# --- V3 status snapshot. Every row cites its source. Recorded 2026-10-15.
SNAPSHOT_DATE = "2026-10-15"
R = "https://github.com/Mozar-Team/factory-that-builds-itself"
SNAPSHOT_V3 = {
    "recovery": {
        "title": "Retreat merged: FLOW-RECOVERY-001",
        "pr": f"{R}/pull/115",
        "state": "Accepted by you on 2026-10-15 05:41 UTC (ACCEPT FLOW-RECOVERY-001 GOVERNANCE) and merged on 2026-10-21 06:29 UTC as eb65363. Flow V3 is gone; see the Current flow tab.",
        "removes": ["Event controller and its workflow (flow-auto-events.yml)", "Local runner and native session adapters", "Paired writer admission (writer-admission.yml)", "Runner documentation (FLOW_AUTO_RUNNER.md)", "Their tests"],
        "keeps": ["Task contract in the PR", "Your ACCEPT before any write", "One active writer at a time", "Independent QC in a separate session", "Start and final preflight", "Your playtest receipt and manual merge"],
        "adds": ["contract.py: one shared contract parser", "governance-guard.yml: trusted check for governance paths", "docs/briefs/HUD-SPRITE-001.md: the HUD brief for #113"],
        "numbers": [("28", "files changed"), ("+2,724", "lines added"), ("−12,967", "lines removed"), ("357 → 81", "lines in the policy file")],
        "src": [("PR #115", f"{R}/pull/115"), ("ACCEPT", f"{R}/pull/115#issuecomment-6185317650"), ("#114 closed", f"{R}/pull/114#issuecomment-6185490239")],
        "cmd": "git diff --shortstat 3370cfc eb65363; git show 3370cfc:.codex/workflow-policy.toml | wc -l; git show eb65363:.codex/workflow-policy.toml | wc -l",
    },
    "summary": "Before the retreat: the automation ran, but no task could move through it. The event workflow fires and finishes green, yet the two open flow tasks are blocked and game work waits behind them.",
    "components": [
        {"name": "Event workflow (flow-auto-events.yml)", "state": "ok",
         "status": "Running. 100 most recent runs: 91 green, 9 red (13–15 Oct).",
         "note": "Green means the controller ran, not that a task moved. PR #110 states this as its main weak point.",
         "src": [("runs API", f"{R}/actions/workflows/flow-auto-events.yml")]},
        {"name": "Self-hosted runner", "state": "warn",
         "status": "One Windows runner on the Product Owner's machine. Jobs still complete on 15 Oct.",
         "note": "Live runner registration could not be read: the GitHub proxy denies the runners API. One runner serializes all jobs by design.",
         "src": [("policy: automation.runner_labels", f"{R}/blob/main/.codex/workflow-policy.toml")]},
        {"name": "Workflow canary", "state": "warn",
         "status": "Last pass 2026-10-11 02:08 UTC on 4d834d4, after failed dispatch runs on 10 Oct.",
         "note": "Not rerun since. main has moved six merges ahead (to 3370cfc).",
         "src": [("canary run", f"{R}/actions/runs/38104153978")]},
        {"name": "Credential canary (#114)", "state": "ok",
         "status": "Passed 2026-10-14. The writer process can authenticate to GitHub.",
         "note": "Fixed the HTTP 404/401 that ended the first writer attempt.",
         "src": [("comment", f"{R}/pull/114#issuecomment-6173375121")]},
        {"name": "Native session adapters", "state": "bad",
         "status": "Defect: resuming a session does not pin model and effort.",
         "note": "A QC session set to gpt-6-astra/low resumed as gpt-5.6-sol/medium. This breaks the effort rules of the policy.",
         "src": [("defect report", f"{R}/pull/113#issuecomment-6159838980")]},
        {"name": "Writer launch", "state": "bad",
         "status": "Two attempts on #114, both BLOCKED before any change.",
         "note": "Attempt 1: GitHub HTTP 404/401. Attempt 2: the runner's fixed writer prompt says \"Do not … alter policy\" (local_runner.py:1668), but the accepted contract requires a policy edit; the writer refused.",
         "src": [("attempt 2", f"{R}/pull/114#issuecomment-6174314657"), ("prompt", f"{R}/blob/main/scripts/workflow/local_runner.py#L1668")]},
        {"name": "Task queue (replenishment)", "state": "warn",
         "status": "16 graphics tasks in NEXT, none marked po-ready.",
         "note": "By design the automation prepares none of them until you mark one.",
         "src": [("TASKS.md NEXT", f"{R}/blob/main/TASKS.md")]},
    ],
    "chain": [
        {"id": "#113", "title": "HUD-SPRITE-001", "state": "bad", "why": "Native launch blocked until model/effort pinning is fixed.", "url": f"{R}/pull/113"},
        {"id": "#114", "title": "FLOW-NATIVE-ROLE-PIN-001", "state": "frozen", "why": "Fix for the pinning defect. Two blocked writer attempts. Closed 15 Oct 05:53 UTC by your decision in #115; the adapter it would fix is removed.", "url": f"{R}/pull/114"},
        {"id": "#110", "title": "FLOW-AUTO-CONTINUITY-001", "state": "frozen", "why": "Repair budget 2/2 used. Writer authority withdrawn, kept as evidence.", "url": f"{R}/pull/110"},
    ],
    "last_merges": "Last game change merged: GENERATOR-BURN-001 (#111) on 2026-10-13. Last process change merged: GFX-QUEUE-TRACKER-001 (#112) on 2026-10-14.",
    "next": [
        "Done: #115 merged on 21 Oct.",
        "Done: HUD restarted as #116 under the lean flow; #113 closed.",
        "Open: Independent QC on #116.",
    ],
}

# --- Governance view: controls in this repo, read as a reusable AI-delivery governance pattern.
# The framework column is the writer's mapping, not a certification.
CONTROLS = [
    {"control": "Human approval before any change", "how": "Your ACCEPT line on the PR, checked by GitHub API author; process files need ACCEPT … GOVERNANCE.",
     "keys": ["contract.accept_line", "contract.governance_accept_line"], "maps": "Human oversight (EU AI Act Art. 14); NIST AI RMF Govern/Manage"},
    {"control": "Separation of duties", "how": "QC is a separate read-only session that must differ from the writer, preferably another provider.",
     "keys": ["gates.qc_session_differs_from_writer", "gates.cross_provider_qc_preferred"], "maps": "Four-eyes principle; ISO/IEC 42001 roles and responsibilities"},
    {"control": "Least privilege", "how": "Reviewers, Architect and QC are read-only; one active writer in the repository.",
     "keys": ["read_only_agents", "gates.one_active_writer"], "maps": "Access control"},
    {"control": "Scope control", "how": "The contract lists allowed files; start preflight rejects anything outside them.",
     "keys": ["contract.fields", "gates.start_command"], "maps": "Change management"},
    {"control": "Risk-based routing", "how": "Listed categories force the heavier ELEVATED route and cannot be downgraded.",
     "keys": ["routing.forced_elevated_categories", "routing.forced_elevated_may_downgrade"], "maps": "Risk tiering (EU AI Act, NIST Map)"},
    {"control": "Bounded retries", "how": "Two failed QC verdicts stop the task until you decide.",
     "keys": ["repair.limit", "repair.stop_status"], "maps": "Incident escalation"},
    {"control": "Evidence trail", "how": "Every verdict is a PR comment bound to an exact commit; every number needs the command that reproduces it.",
     "keys": ["gates.qc_comment_fields"], "maps": "Record keeping and traceability (EU AI Act Art. 12)"},
    {"control": "No autonomous release", "how": "Agents never merge; your playtest receipt is bound to the exact head and base.",
     "keys": ["automatic_merge", "playtest.receipt_fields"], "maps": "Release approval"},
    {"control": "Governance guard", "how": "A trusted check on main keeps process-file changes red until your GOVERNANCE approval exists.",
     "keys": ["gates.governance_status", "contract.governance_prefixes"], "maps": "Segregation of policy changes"},
    {"control": "Complexity budget", "how": "Process code may not grow past a fixed number of lines. Added after V3 grew to 6,867 lines.",
     "keys": ["gates.production_python_line_budget"], "maps": "Cost of control (writer's addition, no framework equivalent)"},
    {"control": "Model and effort discipline", "how": "High effort only for Architect and writer; QC starts low. Now a prose rule in AGENTS.md, no longer a policy key.",
     "keys": ["session_usage.high_effort_allowed_roles"], "maps": "Cost and capability control"},
    {"control": "Proof before rollout (canary)", "how": "Automation had to pass a live canary. Removed together with the automation.",
     "keys": ["automation.capability_canary_required_before_rollout"], "maps": "Validation before deployment"},
]

GAPS = [
    ("Enforcement depends on agent obedience", "Validators check declarations, not behaviour. Schema 5 said so explicitly (`runtime_obedience_is_machine_provable = false`); schema 6 dropped the key, not the limit."),
    ("Single human approver", "Every gate is one person. A company needs roles, delegation and approver rotation."),
    ("Identity is a GitHub login", "No SSO, no per-user roles beyond the Product Owner ID check in po-playtest."),
    ("Evidence lives in PR comments", "No retention policy, no export to an audit store, no tamper evidence beyond GitHub history."),
    ("Governance cost was high", "V3 had 6,867 lines of production process code and stalled game work for days. Schema 6 cut it to 1,456 and capped it at 2,500 (see History)."),
    ("Tied to one repository and two providers", "Policy keys, paths and adapters are specific to this project."),
]

# --- Current flow (schema 6, merged 2026-10-21 by FLOW-RECOVERY-001 #115).
# The policy no longer lists step sequences; the steps below follow
# docs/workflow/SHIP_WORKFLOW.md ("What the Product Owner does" and "Gates").
ARCHIVE_REF = "3370cfc"
ARCHIVE_NOTE = "Rules at 3370cfc (14 Oct), before FLOW-RECOVERY-001. Replaced by schema 6 on 21 Oct."

V4_STEPS = [
    {"name": "brief", "title": "A brief is written", "actor": "writer", "src": "po",
     "plain": "You say \"przygotuj brief X\". An agent writes the brief as DRAFT, then READY.",
     "inputs": ["Your request", "Game documents"], "outputs": ["Brief file marked READY"],
     "gate": "", "tech": ["File: `docs/briefs/X.md`"]},
    {"name": "start", "title": "Task is started", "actor": "orch", "src": "po",
     "plain": "You say \"start X\". The orchestrator picks the route, asks the reviewers, gets an Architect specification if needed and opens a draft PR with a PROPOSED contract.",
     "inputs": ["READY brief"], "outputs": ["Draft PR with the PROPOSED contract"],
     "gate": "A PROPOSED contract holds no writer slot.",
     "tech": ["Contract schema 6 from `.github/pull_request_template.md`", "Check: `python scripts/workflow/preflight.py check-proposed --body-file <body>`"]},
    {"name": "accept", "title": "You approve (ACCEPT)", "actor": "po", "src": "orch",
     "plain": "You comment ACCEPT X on the PR. For changes to process files you add GOVERNANCE. The contract becomes ACTIVE.",
     "inputs": ["PROPOSED contract"], "outputs": ["Your ACCEPT comment"],
     "gate": "The governance guard stays red until your GOVERNANCE line exists.",
     "tech": ["Lines: `ACCEPT <task_id>`, `ACCEPT <task_id> GOVERNANCE`", "Author checked through the GitHub API", "Status: `governance-accept`"]},
    {"name": "start-preflight", "title": "Start check", "actor": "ci", "src": "po",
     "plain": "A script checks the base is current, the tree is clean, Godot is available, no other task is ACTIVE and the change stays inside the allowed files.",
     "inputs": ["ACTIVE contract"], "outputs": ["Go or stop"],
     "gate": "Only one active writer in the whole repository.",
     "tech": ["`python scripts/workflow/preflight.py start --pr N --writer P --writer-session S`"]},
    {"name": "implementation", "title": "Writer builds the change", "actor": "writer", "src": "ci",
     "plain": "The writer makes the smallest accepted change, runs the tests and stops with a comment naming the exact version to check.",
     "inputs": ["ACTIVE contract"], "outputs": ["Change", "Test results", "PENDING VERIFICATION comment"],
     "gate": "Stops and waits for QC.", "tech": ["Godot headless suites via `scripts/workflow/run_godot_checks.py`"]},
    {"name": "ci", "title": "Automated checks", "actor": "ci", "src": "writer",
     "plain": "GitHub validates the rules, keeps the process code under its size budget and runs the game headless.",
     "inputs": ["Latest version"], "outputs": ["Green or red checks"],
     "gate": "Red checks are the writer's to fix.",
     "tech": ["`validate`: policy, the production line budget, all workflow tests", "`Godot 4.7.1 headless smoke check`"]},
    {"name": "qc", "title": "Independent QC", "actor": "qc", "src": "writer",
     "plain": "A separate read-only session, preferably the other provider, checks the change itself and posts PASS, FAIL or BLOCKED.",
     "inputs": ["The exact version to check"], "outputs": ["Seven-line verdict comment"],
     "gate": "FAIL: you say \"popraw\", at most two repairs.",
     "tech": ["QC session must differ from the writer session"]},
    {"name": "closeout", "title": "Result recorded, final check", "actor": "writer", "src": "qc",
     "plain": "After PASS one commit records the result in the task list. A final script checks QC, green CI and that the PR can merge.",
     "inputs": ["PASS verdict"], "outputs": ["Task list entry", "Go for playtest"],
     "gate": "Exactly one commit after QC.",
     "tech": ["`python scripts/workflow/preflight.py final --pr N --qc-comment-url URL ...`"]},
    {"name": "playtest-merge", "title": "You playtest and merge", "actor": "po", "src": "writer",
     "plain": "You get four plain points: what to click, what should happen, what changes, what stays open. You play, post a four-line receipt and merge yourself.",
     "inputs": ["Playtest package"], "outputs": ["PO-PLAYTEST receipt", "Your merge"],
     "gate": "A new push or base needs a new receipt. Agents never merge.",
     "tech": ["Receipt: `PO-PLAYTEST: PASS`, task_id, tested_head_sha, tested_base_sha", "Status: `po-playtest`"]},
]

V4_ELEVATED = [
    "Reviewers for the touched areas are mandatory.",
    "An Architect specification is required for structure, saves, public interfaces, large refactors, several systems or unclear impact.",
    "A findings file is always written; on STANDARD only after a FAIL.",
    "The Architect and the writer may use high effort; QC starts low (AGENTS.md, prose rule).",
]

V4_WHAT_CHANGED = [
    ("Automation", "Event controller, self-hosted runner, native adapters and canary removed.", "self_hosted_runner = false"),
    ("Parallel work", "Two paired writers with server leases replaced by one active writer.", "writer_parallelism = 1"),
    ("Starting a task", "Queue reader and po-ready markers replaced by you saying \"start X\".", "brief + start in SHIP"),
    ("Approval", "ACCEPT codes replaced by a plain line, ACCEPT X, plus GOVERNANCE for process files, checked by a trusted guard.", "contract.accept_line"),
    ("QC comment", "Eight keys to seven: the product field is gone.", "gates.qc_comment_fields"),
    ("Size limit", "New: process code may not exceed a fixed line budget.", "gates.production_python_line_budget"),
]

V4_STATUS = {
    "date": "2026-10-26",
    "pr": f"{R}/pull/116",
    "title": "First task through the lean flow: HUD-SPRITE-001 (#116)",
    "timeline": [
        ("2026-10-21 06:31", "Draft PR opened with the contract", f"{R}/pull/116"),
        ("2026-10-23 17:47", "Your ACCEPT HUD-SPRITE-001", f"{R}/pull/116#issuecomment-6371169433"),
        ("2026-10-24 00:30", "PENDING VERIFICATION at 065a8b0, 31 Godot suites pass, CI 4/4 green", f"{R}/pull/116#issuecomment-6377540838"),
        ("2026-10-26 03:24", "Your decisions \"1A i 2B\": accept a measured performance deviation, move the portrait to a follow-up", f"{R}/pull/116#issuecomment-6407515172"),
    ],
    "now": "Waiting for Independent QC on 065a8b0. No QC verdict on the PR yet.",
    "notes": [
        "ACCEPT to PENDING VERIFICATION took about 6.7 hours, with no runner and no manual rescue recorded on the PR.",
        "The task is large: 71 files, +7,647 / −1,786 lines. QC will need time.",
        "Criterion 1 (retained EVA portrait) is met only by the follow-up task after your decision 2B.",
    ],
}

KNOWN_SECTIONS_V6 = {"routing", "reviewer_mapping", "contract", "gates", "repair", "evidence", "playtest", "automation"}

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
    {"from": "2026-10-15", "to": "2026-10-15", "name": "Retreat (PR open)",
     "what": "FLOW-RECOVERY-001 (#115) removes the event controller, the local runner, paired admission and their tests, and keeps contract, ACCEPT, one writer, independent QC, preflight and the playtest gate. #114 was closed. Not merged yet, so it is not counted below.",
     "lesson": "Removing about 13,000 lines is the first flow change that makes the process smaller."},
]

# --- V3 status snapshot. Every row cites its source. Recorded 2026-10-15.
SNAPSHOT_DATE = "2026-10-15"
R = "https://github.com/Mozar-Team/factory-that-builds-itself"
SNAPSHOT_V3 = {
    "recovery": {
        "title": "Retreat in progress: FLOW-RECOVERY-001",
        "pr": f"{R}/pull/115",
        "state": "Accepted by you on 2026-10-15 05:41 UTC (ACCEPT FLOW-RECOVERY-001 GOVERNANCE). Implementation at 3307237; validate and Godot checks green. Waiting for Independent QC, closeout, your playtest receipt and your merge.",
        "removes": ["Event controller and its workflow (flow-auto-events.yml)", "Local runner and native session adapters", "Paired writer admission (writer-admission.yml)", "Runner documentation (FLOW_AUTO_RUNNER.md)", "Their tests"],
        "keeps": ["Task contract in the PR", "Your ACCEPT before any write", "One active writer at a time", "Independent QC in a separate session", "Start and final preflight", "Your playtest receipt and manual merge"],
        "adds": ["contract.py: one shared contract parser", "governance-guard.yml: trusted check for governance paths", "docs/briefs/HUD-SPRITE-001.md: the HUD brief for #113"],
        "numbers": [("27", "files changed"), ("+2,672", "lines added"), ("−12,967", "lines removed"), ("−276", "net lines in the policy file")],
        "src": [("PR #115", f"{R}/pull/115"), ("ACCEPT", f"{R}/pull/115#issuecomment-6185317650"), ("#114 closed", f"{R}/pull/114#issuecomment-6185490239")],
        "cmd": "curl -s https://api.github.com/repos/Mozar-Team/factory-that-builds-itself/pulls/115 | jq '.changed_files,.additions,.deletions'",
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
        "Independent QC on #115 at 3307237, from a session other than the writer.",
        "Closeout, your playtest receipt, your merge of #115.",
        "Restart #113 (HUD) by hand under the simpler flow, using the brief that #115 adds.",
    ],
}

# --- Governance view: controls in this repo, read as a reusable AI-delivery governance pattern.
# The framework column is the writer's mapping, not a certification.
CONTROLS = [
    {"control": "Human approval before any change", "how": "Product Owner ACCEPT names the route, writer and allowed files before the first write.",
     "key": "lanes.*.product_owner_accept_before_write", "maps": "Human oversight (EU AI Act Art. 14); NIST AI RMF Govern/Manage"},
    {"control": "Separation of duties", "how": "The writer cannot pass its own work; QC is a separate read-only session, preferably from another provider.",
     "key": "permissions.builder_may_issue_qc_pass = false", "maps": "Four-eyes principle; ISO/IEC 42001 roles and responsibilities"},
    {"control": "Least privilege", "how": "Reviewers, Architect and QC are read-only; one writer per task; protected paths need an exclusive slot.",
     "key": "read_only_agents, admission.protected_prefixes", "maps": "Access control"},
    {"control": "Scope control", "how": "The contract lists allowed paths; preflight rejects anything outside them.",
     "key": "preflight.start_required_before_content_commit", "maps": "Change management"},
    {"control": "Risk-based routing", "how": "Listed categories force the heavier ELEVATED route and cannot be downgraded.",
     "key": "routing.forced_elevated_categories", "maps": "Risk tiering (EU AI Act, NIST Map)"},
    {"control": "Bounded retries", "how": "Two failed QC verdicts stop the task until a human decides.",
     "key": "repair.limit", "maps": "Incident escalation"},
    {"control": "Evidence trail", "how": "Every verdict is an immutable PR comment bound to a commit SHA; every number needs the command that reproduces it.",
     "key": "evidence.qc_comment_required", "maps": "Record keeping and traceability (EU AI Act Art. 12)"},
    {"control": "No autonomous release", "how": "Agents never merge; your playtest receipt is bound to the exact code and base.",
     "key": "automatic_merge = false, playtest.invalidated_by", "maps": "Release approval"},
    {"control": "No invented requirements", "how": "Missing product decisions are recommended for you to decide, never applied.",
     "key": "replenishment.invent_requirements = false", "maps": "Accountability of the human owner"},
    {"control": "Proof before rollout", "how": "Automation counts as working only after a live canary passes.",
     "key": "automation.capability_canary_required_before_rollout", "maps": "Validation before deployment"},
    {"control": "Model and effort discipline", "how": "Each role has a fixed model effort; high effort only for Architect, writer and QC.",
     "key": "session_usage.high_effort_allowed_roles", "maps": "Cost and capability control"},
]

GAPS = [
    ("Enforcement depends on agent obedience", "The policy itself says runtime obedience is not machine-provable (`runtime_obedience_is_machine_provable = false`). Validators check declarations, not behaviour."),
    ("Single human approver", "Every gate is one person. A company needs roles, delegation and approver rotation."),
    ("Identity is a GitHub login", "No SSO, no per-user roles beyond the Product Owner ID check in po-playtest."),
    ("Evidence lives in PR comments", "No retention policy, no export to an audit store, no tamper evidence beyond GitHub history."),
    ("Governance cost is high", "Process code is about the same size as game code (estimate, see History), and the current stall shows governance can block delivery for days."),
    ("Tied to one repository and two providers", "Policy keys, paths and adapters are specific to this project."),
]

"""Build the Mazor Ship flow map from .codex/workflow-policy.toml and git history.

Usage: python build.py --repo PATH_TO_GAME_REPO [--ref origin/main] [--out docs/index.html] [--standalone]
Set GITHUB_TOKEN to read the live canary status from the GitHub Actions API.
"""

import argparse
import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import tomllib
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import io_map as M  # noqa: E402

POLICY = ".codex/workflow-policy.toml"
# Protected policy paths are process paths, except the ones that record game work.
NOT_ADMIN = {"project.godot", "TASKS.md", "docs/verification/"}
ID_RE = r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d{3}"


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True, text=True).stdout


def e(s):
    return html.escape(str(s))


def md(s):
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", e(s))


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        out.update(flatten(v, key) if isinstance(v, dict) else {key: v})
    return out


def policy_at(repo, rev):
    try:
        return flatten(tomllib.loads(git(repo, "show", f"{rev}:{POLICY}")))
    except (subprocess.CalledProcessError, tomllib.TOMLDecodeError):
        return {}


def policy_diff(repo, sha):
    new, old = policy_at(repo, sha), policy_at(repo, f"{sha}^")
    return [{"key": k, "kind": "added" if k not in old else "removed" if k not in new else "changed",
             "old": old.get(k), "new": new.get(k)}
            for k in sorted(set(old) | set(new)) if old.get(k) != new.get(k)]


def admin_history(repo, ref, paths):
    raw = git(repo, "log", ref, "--date=short", "--name-only", "--format=\x1e%H\x1f%h\x1f%ad\x1f%s", "--", *paths)
    commits = []
    for block in raw.split("\x1e")[1:]:
        head, *files = block.strip("\n").split("\n")
        sha, short, date, subject = head.split("\x1f")
        files = [f for f in files if f and any(f == p or f.startswith(p) for p in paths)]
        m = re.match(rf"({ID_RE})\b", subject)
        pr = re.search(r"\(#(\d+)\)\s*$", subject)
        commits.append({"sha": sha, "short": short, "date": date, "subject": subject,
                        "task": m.group(1) if m else None, "pr": pr.group(1) if pr else None, "files": files,
                        "policy": policy_diff(repo, sha) if POLICY in files else []})
    return commits


def gh_api(path):
    req = urllib.request.Request("https://api.github.com" + path, headers={"Accept": "application/vnd.github+json"})
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['GITHUB_TOKEN']}")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def canary_status(slug, workflow):
    """Latest non-skipped canary step in the automation workflow, from the Actions API."""
    try:
        runs = gh_api(f"/repos/{slug}/actions/workflows/{workflow}/runs?event=workflow_dispatch&per_page=20")
        for run in runs.get("workflow_runs", []):
            for job in gh_api(f"/repos/{slug}/actions/runs/{run['id']}/jobs").get("jobs", []):
                for step in job.get("steps", []):
                    if "canary" in step["name"].lower() and step["conclusion"] not in (None, "skipped"):
                        return {"ok": step["conclusion"] == "success",
                                "when": run["created_at"].replace("T", " ")[:16] + " UTC",
                                "sha": run["head_sha"][:7], "url": run["html_url"]}
        return {"ok": False, "when": None}
    except Exception:  # noqa: BLE001 — no network or token must not break the build
        return None


def chips(keys, labels=None):
    out = []
    for k in keys:
        lab = (labels or {}).get(k)
        if labels is None:
            out.append(f'<span class="chip raw">{e(k)}</span>')
        elif lab:
            out.append(f'<span class="chip" title="{e(k)}">{e(lab)}</span>')
        else:
            out.append(f'<span class="chip new" title="no description yet">{e(k)}</span>')
    return "".join(out)


def tech(items):
    return f'<details class="tech"><summary>Technical details</summary><ul>{"".join(f"<li>{i}</li>" for i in items)}</ul></details>'


# ---------- Tab 1: flow map ----------

def steps_for(policy, lane):
    out = []
    for i, name in enumerate(policy["lanes"][lane]["sequence"], 1):
        info = M.STEPS.get(name) or {"title": name, "actor": "orch", "src": "orch", "inputs": [], "outputs": [],
                                     "gate": "", "tech": [], "missing": True}
        info = dict(info, name=name, n=i)
        if lane == "STANDARD":
            info["actor"] = M.STANDARD_MERGED_ACTORS.get(info["actor"], info["actor"])
            info["src"] = M.STANDARD_MERGED_ACTORS.get(info["src"], info["src"])
        out.append(info)
    return out


def actor_label(key, lane):
    return "Writer = Orchestrator" if lane == "STANDARD" and key == "writer" else M.ACTORS[key]


def sequence_svg(steps, lane):
    order = ["po", "orch", "rev", "arch", "writer", "ci", "qc"]
    used = {s["actor"] for s in steps} | {s["src"] for s in steps}
    cols = [a for a in order if a in used]
    colw, top, rowh, left = 150, 70, 64, 20
    width, height = left * 2 + colw * len(cols), top + rowh * len(steps) + 30
    x = {a: left + colw * i + colw / 2 for i, a in enumerate(cols)}
    p = [f'<svg class="seq" viewBox="0 0 {width} {height}" width="{width}" role="img" aria-label="{lane} sequence diagram">',
         f'<defs><marker id="ah-{lane}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
         'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="ahead"/></marker></defs>']
    for a in cols:
        p.append(f'<line x1="{x[a]}" y1="{top - 16}" x2="{x[a]}" y2="{height - 10}" class="life"/>')
        p.append(f'<rect x="{x[a] - 66}" y="10" width="132" height="40" rx="6" class="actor a-{a}"/>')
        p.append(f'<text x="{x[a]}" y="35" class="actor-t">{e(actor_label(a, lane))}</text>')
    for i, s in enumerate(steps):
        y = top + rowh * i + 30
        x1, x2 = x[s["src"]], x[s["actor"]]
        cls = "msg warn" if s.get("missing") else "msg"
        if x1 == x2:
            p.append(f'<path d="M{x1},{y - 10} h34 v20 h-30" class="{cls}" marker-end="url(#ah-{lane})"/>')
            tx, anchor = x1 + 42, "start"
        else:
            d = 1 if x2 > x1 else -1
            p.append(f'<line x1="{x1}" y1="{y}" x2="{x2 - 14 * d}" y2="{y}" class="{cls}" marker-end="url(#ah-{lane})"/>')
            tx, anchor = (x1 + x2) / 2, "middle"
        p.append(f'<circle cx="{x2}" cy="{y}" r="11" class="dot a-{s["actor"]}"/>')
        p.append(f'<text x="{x2}" y="{y + 4}" class="dot-t">{s["n"]}</text>')
        p.append(f'<text x="{tx}" y="{y - 10}" text-anchor="{anchor}" class="msg-t">{e(s["title"])}</text>')
        if s["outputs"]:
            out = s["outputs"][0].replace("`", "")
            out = out if len(out) < 44 else out[:42] + "…"
            p.append(f'<text x="{tx}" y="{y + 22}" text-anchor="{anchor}" class="msg-s">→ {e(out)}</text>')
    p.append("</svg>")
    return "\n".join(p)


def step_cards(steps, lane):
    cards = []
    for s in steps:
        warn = '<p class="warn-t">This step is in the policy but has no description on this page yet.</p>' if s.get("missing") else ""
        ul = lambda xs: "".join(f"<li>{md(x)}</li>" for x in xs) or "<li>—</li>"
        t = [md(x) for x in s.get("tech", [])] + [f"Step id: <code>{e(s['name'])}</code>"]
        cards.append(f"""
<article class="step" id="{lane.lower()}-{s['n']}">
  <header><span class="num a-{s['actor']}">{s['n']}</span>
    <div><h4>{e(s['title'])}</h4><p class="meta"><span class="who">{e(actor_label(s['actor'], lane))}</span></p></div></header>
  {warn}
  {f'<p class="plain">{md(s["plain"])}</p>' if s.get('plain') else ''}
  <div class="io"><div><h5>Gets</h5><ul>{ul(s['inputs'])}</ul></div><div><h5>Gives</h5><ul>{ul(s['outputs'])}</ul></div></div>
  {f'<p class="gate"><b>Stops when</b> {md(s["gate"])}</p>' if s['gate'] else ''}
  {tech(t)}
</article>""")
    return "\n".join(cards)


def lane_section(policy, lane):
    cfg = policy["lanes"][lane]
    steps = steps_for(policy, lane)
    arch = {False: "no", True: "always", "conditional_by_category": "depends on category"}.get(
        cfg.get("architect_specification_required"), cfg.get("architect_specification_required"))
    facts = [("Separate AI sessions", cfg.get("sessions_required")),
             ("Your approval first", "yes" if cfg.get("product_owner_accept_before_write") else "no"),
             ("Independent check", "yes" if cfg.get("independent_qc_after_write") else "no"),
             ("Who merges", "only you" if cfg.get("manual_product_owner_merge") else "?"),
             ("Architect", arch)]
    facts_html = "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in facts)
    return f"""
<div class="lane" data-lane="{lane}" {'hidden' if lane != policy['default_lane'] else ''}>
  <dl class="facts">{facts_html}</dl>
  <p class="lede">{e(M.LANE_INTRO.get(lane, ""))}</p>
  <div class="scroll">{sequence_svg(steps, lane)}</div>
  <div class="steps">{step_cards(steps, lane)}</div>
</div>"""


def automation_section(policy, canary):
    a, pt, rp = policy.get("automation", {}), policy.get("playtest", {}), policy.get("replenishment", {})
    if not a:
        return ""
    never = [(a.get("automatic_accept") is False, "approve (ACCEPT) for you"),
             (a.get("automatic_merge") is False, "merge changes"),
             (a.get("schedule_triggers") is False, "run on a timer"),
             (a.get("unchanged_state_polling") is False, "poll when nothing changed"),
             (a.get("blind_retry") is False, "retry failed actions blindly"),
             (a.get("event_text_executed") is False, "execute comment text"),
             (rp.get("invent_requirements") is False, "invent requirements"),
             (rp.get("recommended_values_auto_applied") is False, "apply its own recommendations")]
    never_html = "".join(f"<li>{e(t)}</li>" for ok, t in never if ok)
    if canary is None:
        can = '<p class="pill unk">Canary status: this build could not read it from GitHub.</p>'
    elif canary["ok"]:
        can = (f'<p class="pill ok">Last canary passed {e(canary["when"])} on {e(canary["sha"])}. '
               f'<a href="{e(canary["url"])}">run</a></p>')
    else:
        can = '<p class="pill bad">The last canary did not pass. The automation does not count as working.</p>'
    wf = Path(a.get("event_workflow", "")).name
    t = [f"Controller: <code>{e(a.get('event_controller'))}</code>",
         f"Workflow: <code>{e(a.get('event_workflow'))}</code>, only from <code>{e(a.get('trusted_ref'))}</code>",
         f"Runner labels: {chips(a.get('runner_labels', []))}",
         f"Events: {chips(a.get('routed_events', []))}",
         f"Also woken when these finish: {chips(a.get('workflow_run_sources', []))}",
         f"Profile schema {e(a.get('profile_schema_version'))}, journal schema {e(a.get('journal_schema_version'))}",
         f"Notifications: <code>{e(a.get('notification_transport'))}</code>",
         f"Canary: <code>gh workflow run {e(wf)} --ref main -f mode=canary -f pr=0</code>",
         f"Playtest: check <code>{e(pt.get('required_check'))}</code>, script <code>{e(pt.get('script'))}</code>, invalidated by {chips(pt.get('invalidated_by', []))}",
         f"Queue: <code>{e(rp.get('queue_authority'))}</code>, marker <code>{e(rp.get('eligibility_marker'))}</code>"]
    return f"""
<section id="automation">
  <header>
    <h2>The automation (runner)</h2>
    <p class="lede">A runner on your Windows machine moves tasks between steps by itself. A GitHub event wakes it: a comment, a new commit, finished checks. Each time it does at most one thing and goes back to waiting.</p>
  </header>
  {can}
  <div class="cards">
    <div class="card"><h3>What it does by itself</h3><ul>
      <li>Picks tasks you marked as ready when a writer is free.</li>
      <li>Prepares the contract. If a product decision is missing, it recommends one and you decide.</li>
      <li>Starts the writer, then a separate QC session, then records the result.</li>
      <li>After each action it wakes once more to see if there is a next step.</li>
    </ul></div>
    <div class="card"><h3>What it never does</h3><ul>{never_html}</ul></div>
    <div class="card"><h3>When it messages you</h3><div class="chips">{chips(a.get('notification_states', []), M.NOTIFY_LABELS)}</div>
      <h3 class="mt">When it stops</h3><div class="chips">{chips(rp.get('stop_outcomes', []), M.STOP_LABELS)}</div></div>
    <div class="card"><h3>Your playtest</h3><p>After playing you leave a comment with your verdict. A GitHub check confirms you wrote it. Any new code or base version invalidates the confirmation, so you play again.</p></div>
  </div>
  {tech(t)}
</section>"""


def unknown_sections(policy, known):
    new = [k for k, v in policy.items() if isinstance(v, dict) and k not in known]
    if not new:
        return ""
    return ('<p class="warn-t">The policy has new sections this page does not describe yet: '
            + ", ".join(f"<code>{e(k)}</code>" for k in new) + ". Add them to io_map.py.</p>")


# ---------- Tab 0: current flow ----------

def workflow_json(policy):
    """The current flow as one JSON document, from the same data the page draws."""
    g, c, r = policy.get("gates", {}), policy.get("contract", {}), policy.get("repair", {})
    doc = {"workflow": {
        "name": "Mazor Ship", "contract_schema": c.get("schema_version"),
        "rules": {"active_writers": policy.get("writer_parallelism"), "repair_limit": r.get("limit"),
                  "automatic_merge": policy.get("automatic_merge"), "accept_line": c.get("accept_line"),
                  "governance_accept_line": c.get("governance_accept_line"),
                  "production_python_line_budget": g.get("production_python_line_budget"),
                  "qc_comment_fields": g.get("qc_comment_fields")},
        "groups": [{"id": grp["id"], "name": grp["name"],
                    "nodes": [dict({"label": n["label"], "actor": M.ACTORS[n["actor"]], "step": n["step"]},
                                   **({"optional": True} if n.get("optional") else {})) for n in grp["nodes"]]}
                   for grp in M.V4_CANVAS],
        "steps": [{"id": i, "name": st["name"], "title": st["title"], "actor": M.ACTORS[st["actor"]],
                   "inputs": [x.replace("`", "") for x in st["inputs"]],
                   "outputs": [x.replace("`", "") for x in st["outputs"]],
                   **({"stops_when": st["gate"].replace("`", "")} if st["gate"] else {})}
                  for i, st in enumerate(M.V4_STEPS, 1)],
    }}
    return json.dumps(doc, indent=2, ensure_ascii=False)


def canvas_html(policy):
    groups = []
    for gi, grp in enumerate(M.V4_CANVAS):
        nodes = "".join(
            f'<a class="node{" opt" if n.get("optional") else ""}" href="#v4-{n["step"]}" title="Step {n["step"]}: {e(M.ACTORS[n["actor"]])}">'
            f'<span class="ico a-{n["actor"]}">{M.ACTOR_SHORT[n["actor"]]}</span><span class="lbl">{e(n["label"])}</span></a>'
            for n in grp["nodes"])
        groups.append(f'<div class="grp g-{grp["color"]}"><h4><span>{gi + 1}</span>{e(grp["name"])}</h4><div class="nodes">{nodes}</div></div>')
    legend = "".join(f'<span><i class="ico a-{k}">{v}</i>{e(M.ACTORS[k])}</span>' for k, v in M.ACTOR_SHORT.items())
    return f"""
<section>
  <header><h3>The flow as a workflow</h3><p class="lede">Five stages, left to right. Dashed nodes run only when needed. Click a node to jump to its card; the JSON on the right is the same flow as data.</p></header>
  <div class="board">
    <div class="canvas">
      <div class="grps">{''.join(groups)}</div>
      <p class="loop-note">Verify → Build: a FAIL sends the task back for a repair, at most {e(policy.get('repair', {}).get('limit'))} times, then it stops for your decision.</p>
      <div class="legend">{legend}</div>
    </div>
    <div class="out">
      <div class="out-h"><span>Output</span><button type="button" id="copy-json">Copy JSON</button></div>
      <pre id="wf-json">{e(workflow_json(policy))}</pre>
    </div>
  </div>
</section>"""

def current_tab(policy):
    g, c, r = policy.get("gates", {}), policy.get("contract", {}), policy.get("repair", {})
    steps = [dict(st, n=i) for i, st in enumerate(M.V4_STEPS, 1)]
    st = M.V4_STATUS
    budget = g.get("production_python_line_budget")
    facts = [("Active writers", policy.get("writer_parallelism")), ("Repairs before stop", r.get("limit")),
             ("QC comment lines", len(g.get("qc_comment_fields", []))), ("Runner", "none" if policy.get("automation", {}).get("self_hosted_runner") is False else "yes"),
             ("Who merges", "only you" if policy.get("manual_merge_required") else "?")]
    facts_html = "".join(f"<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>" for k, v in facts)
    changed = "".join(f"<tr><td><b>{e(a)}</b></td><td>{e(b)}</td><td><code>{e(k)}</code></td></tr>" for a, b, k in M.V4_WHAT_CHANGED)
    rows = "".join(f'<tr><td><a href="{M.R}/pull/{n}">#{n}</a></td><td>{e(t)}</td><td>{e(a)}</td><td>{e(q)}</td><td>{e(m)}</td><td class="hrs">{h:.1f} h</td></tr>'
                   for n, t, a, q, m, h in st["rows"])
    notes = "".join(f"<li>{e(n)}</li>" for n in st["notes"])
    elev = "".join(f"<li>{md(x)}</li>" for x in M.V4_ELEVATED)
    t = [f"Contract schema {e(c.get('schema_version'))}, fields: {chips(c.get('fields', []))}",
         f"Process paths needing GOVERNANCE: {chips(c.get('governance_prefixes', []))}",
         f"QC comment fields: {chips(g.get('qc_comment_fields', []))}",
         f"Production line budget: {e(budget)}",
         f"Stop status after the limit: <code>{e(r.get('stop_status'))}</code>"]
    return f"""
<section>
  <header>
    <p class="eyebrow">In force since 2026-10-21 · schema {e(policy.get('schema_version'))}</p>
    <h2>Current flow (V4, lean)</h2>
    <p class="lede">After the retreat the flow is a short chain of gates with no automation. You start every task by saying so, approve it with one line, and play and merge it yourself. One writer works at a time.</p>
    <p class="note">"V4" is this page's name. The repository calls it SHIP, contract schema 6.</p>
  </header>
  {unknown_sections(policy, M.KNOWN_SECTIONS_V6)}
  <dl class="facts">{facts_html}</dl>
</section>
{canvas_html(policy)}
<section>
  <header><h3>The chain</h3><p class="lede">The same chain for both routes. The number on the diagram is the card below it.</p></header>
  <div class="scroll">{sequence_svg(steps, "V4")}</div>
  <div class="steps">{step_cards(steps, "V4")}</div>
  <div class="card mt"><h4>On the ELEVATED route, also</h4><ul>{elev}</ul></div>
  {tech(t)}
</section>
<section>
  <header><h3>What changed from V3</h3></header>
  <div class="scroll" style="padding:0"><table class="controls"><thead><tr><th>Area</th><th>Now</th><th>Where</th></tr></thead><tbody>{changed}</tbody></table></div>
</section>
<section class="recovery">
  <header>
    <p class="eyebrow">Live check · {e(st['date'])}</p>
    <h3>{e(st['title'])}</h3>
    <p class="lede">{e(st['now'])}</p>
  </header>
  <div class="scroll" style="padding:0"><table class="controls"><thead><tr><th>PR</th><th>Task</th><th>ACCEPT</th><th>QC</th><th>Merged</th><th>ACCEPT → merge</th></tr></thead><tbody>{rows}</tbody></table></div>
  <ul class="notes mt">{notes}</ul>
  {tech([f"Source: {e(st['cmd'])}"])}
</section>"""


# ---------- Tab 2: V3 status ----------

STATE_LABEL = {"ok": "working", "warn": "needs attention", "bad": "broken", "frozen": "frozen"}


def v3_tab():
    s = M.SNAPSHOT_V3
    comps = "".join(f"""
<article class="status s-{c['state']}">
  <header><h4>{e(c['name'])}</h4><span class="badge b-{c['state']}">{STATE_LABEL[c['state']]}</span></header>
  <p>{e(c['status'])}</p>
  <p class="note">{e(c['note'])}</p>
  <p class="src">{' · '.join(f'<a href="{e(u)}">{e(n)}</a>' for n, u in c['src'])}</p>
</article>""" for c in s["components"])
    chain = "".join(f"""
<li class="link s-{c['state']}"><a href="{e(c['url'])}"><b>{e(c['id'])}</b> {e(c['title'])}</a>
  <span class="badge b-{c['state']}">{STATE_LABEL[c['state']]}</span><p>{e(c['why'])}</p></li>""" for c in s["chain"])
    nxt = "".join(f"<li>{e(n)}</li>" for n in s["next"])
    counts = {k: sum(1 for c in s["components"] if c["state"] == k) for k in ("ok", "warn", "bad")}
    rec = s.get("recovery")
    rec_html = ""
    if rec:
        li = lambda xs: "".join(f"<li>{e(x)}</li>" for x in xs)
        nums = "".join(f'<div><b>{e(n)}</b><span>{e(l)}</span></div>' for n, l in rec["numbers"])
        rec_html = f"""
<section class="recovery">
  <header>
    <p class="eyebrow">Latest · {e(M.SNAPSHOT_DATE)}</p>
    <h2><a href="{e(rec['pr'])}">{e(rec['title'])}</a></h2>
    <p class="lede">{e(rec['state'])}</p>
  </header>
  <div class="tally nums">{nums}</div>
  <div class="cards mt">
    <div class="card"><h4>Removed</h4><ul>{li(rec['removes'])}</ul></div>
    <div class="card"><h4>Kept</h4><ul>{li(rec['keeps'])}</ul></div>
    <div class="card"><h4>Added</h4><ul>{li(rec['adds'])}</ul></div>
  </div>
  <p class="src mt">{' · '.join(f'<a href="{e(u)}">{e(n)}</a>' for n, u in rec['src'])}</p>
  {tech([f"Numbers: <code>{e(rec['cmd'])}</code>"])}
</section>"""
    return rec_html + f"""
<section>
  <header>
    <p class="eyebrow">Snapshot recorded {e(M.SNAPSHOT_DATE)}, before the retreat</p>
    <h2>Flow V3: what worked and what did not</h2>
    <p class="lede">{e(s['summary'])}</p>
  </header>
  <div class="tally">
    <div class="t-ok"><b>{counts['ok']}</b><span>working</span></div>
    <div class="t-warn"><b>{counts['warn']}</b><span>need attention</span></div>
    <div class="t-bad"><b>{counts['bad']}</b><span>broken</span></div>
  </div>
</section>
<section>
  <header><h3>Why nothing moved</h3><p class="lede">Game work waited on a fix to the automation, and that fix was itself stuck.</p></header>
  <ol class="chain">{chain}</ol>
  <p class="lede mt">{e(s['last_merges'])}</p>
</section>
<section>
  <header><h3>Components</h3></header>
  <div class="statuses">{comps}</div>
</section>
<section>
  <header><h3>Outcome</h3><p class="lede">What happened after the snapshot, from the PRs.</p></header>
  <ol class="next">{nxt}</ol>
</section>"""


# ---------- Tab 3: governance ----------

def key_cells(keys, flat):
    out = []
    for k in keys:
        present = k in flat or any(f.startswith(k + ".") for f in flat)
        out.append(f'<div class="key {"in" if present else "out"}"><code>{e(k)}</code>'
                   f'<span>{"in policy" if present else "not in current policy"}</span></div>')
    return "".join(out)


def governance_tab(policy):
    flat = flatten(policy)
    rows = []
    for c in M.CONTROLS:
        rows.append(f"""<tr><td><b>{e(c['control'])}</b><p>{e(c['how'])}</p></td>
<td class="maps">{e(c['maps'])}</td><td>{key_cells(c['keys'], flat)}</td></tr>""")
    gaps = "".join(f"<li><b>{e(t)}</b><p>{md(d)}</p></li>" for t, d in M.GAPS)
    n_keys = len(flat)
    return f"""
<section>
  <header>
    <h2>Governance: the flow as an AI delivery framework</h2>
    <p class="lede">The same rules that keep AI agents in line on this game are a general pattern for any team that lets AI write production changes: a human approves, AI builds, a different AI checks, a human releases, and everything leaves evidence.</p>
  </header>
  <p class="warn-t">Weak point first: this is one person's project. It has never run in a company, with several approvers, an auditor or a compliance team. The framework column below is the writer's mapping, not a certification.</p>
</section>
<section>
  <header><h3>The pattern in five gates</h3></header>
  <ol class="road">
    <li><b>Intent</b><span>a human states the outcome</span></li>
    <li><b>Contract</b><span>AI writes scope, plan, tests</span></li>
    <li><b>Approval</b><span>a human accepts and assigns</span></li>
    <li><b>Build + verify</b><span>one AI builds, another checks</span></li>
    <li><b>Release</b><span>a human tests and merges</span></li>
  </ol>
</section>
<section>
  <header><h3>Controls</h3><p class="lede">{len(M.CONTROLS)} controls. The key column is checked against the current policy ({n_keys} keys): a control whose key is gone is now prose only or removed.</p></header>
  <div class="scroll" style="padding:0"><table class="controls"><thead><tr><th>Control</th><th>Related framework idea</th><th>Policy key</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
</section>
<section>
  <header><h3>What a company would still need</h3></header>
  <ul class="gaps">{gaps}</ul>
</section>
<section>
  <header><h3>What V3 and its retreat teach about the product</h3></header>
  <div class="cards">
    <div class="card"><h4>Kept the system safe</h4><p>The writer refused to break a rule (\"do not alter policy\") even when its own contract asked for it. Nothing unapproved reached main.</p></div>
    <div class="card"><h4>Stopped delivery</h4><p>That refusal, plus the model/effort defect, left game work waiting from 13 Oct until the retreat merged on 21 Oct. Safety and throughput pull against each other.</p></div>
    <div class="card"><h4>The fix was subtraction</h4><p>Schema 6 kept the gates and removed the machinery: 357 → 81 policy lines, 6,867 → 1,456 lines of process code, and a budget so it cannot grow back unnoticed.</p></div>
    <div class="card"><h4>What to sell, if anything</h4><p>Not the code: the contract format, the gate sequence and the evidence rules. Those transfer between companies; runners and adapters do not.</p></div>
  </div>
</section>"""


# ---------- Tab 4: history ----------

def prod_lines(repo, rev):
    """Production workflow Python lines at rev, counted like validate_agent_config.production_lines."""
    names = [n for n in git(repo, "ls-tree", "--name-only", f"{rev}:scripts/workflow").split()
             if n.endswith(".py") and not n.startswith("test_")] if rev else []
    return sum(len(git(repo, "show", f"{rev}:scripts/workflow/{n}").splitlines()) for n in names)


def bar_rows(rows):
    top = max(v for _, v in rows) or 1
    return "".join(f'<div class="bar"><span class="lab">{e(n)}</span><span class="track"><span style="width:{v / top * 100:.0f}%"></span></span><span class="val">{v:,}</span></div>' for n, v in rows)

def tracker(commits):
    groups = {}
    for c in commits:
        groups.setdefault(c["task"] or c["subject"], []).append(c)
    rows = []
    for key, cs in groups.items():
        files = sorted({f for c in cs for f in c["files"]})
        pol = [ch for c in cs for ch in c["policy"]]
        prs = sorted({c["pr"] for c in cs if c["pr"]}, key=int)
        date = max(c["date"] for c in cs)
        what = re.sub(r"\s*\(#\d+\)\s*$", "", re.sub(rf"^{ID_RE}\s*[:—–-]\s*", "", cs[-1]["subject"])).strip() or key
        pol_html = ""
        if pol:
            items = "".join(
                f'<li><span class="k">{e(ch["kind"])}</span> <code>{e(ch["key"])}</code>'
                + (f' <span class="old">{e(json.dumps(ch["old"], ensure_ascii=False))}</span>' if ch["old"] is not None else "")
                + (f' → <span class="new">{e(json.dumps(ch["new"], ensure_ascii=False))}</span>' if ch["new"] is not None else "")
                + "</li>" for ch in pol[:40])
            more = f"<li>… and {len(pol) - 40} more</li>" if len(pol) > 40 else ""
            pol_html = f'<h5>Policy keys changed</h5><ul class="pol">{items}{more}</ul><h5>Commits and files</h5>'
        commit_list = "".join(f'<li><code>{e(c["short"])}</code> {e(c["date"])} {e(c["subject"])}</li>' for c in cs)
        file_list = "".join(f"<li><code>{e(f)}</code></li>" for f in files)
        areas = sorted({next((lab for pre, lab in M.AREAS if f.startswith(pre)), f) for f in files})
        rows.append(f"""
<li class="entry" data-search="{e((key + ' ' + what + ' ' + ' '.join(files)).lower())}">
  <div class="when">{e(date)}</div>
  <div class="what">
    <h4>{e(what)}</h4>
    <p class="meta"><code>{e(key)}</code>{''.join(f' <span class="pr">PR #{p}</span>' for p in prs)}</p>
    <p class="areas">{''.join(f'<span class="chip">{e(x)}</span>' for x in areas)}{'<span class="chip hot">rule change</span>' if pol else ''}</p>
    <details class="tech"><summary>Technical details: {len(cs)} commits, {len(files)} files{f', {len(pol)} policy keys' if pol else ''}</summary>
      {pol_html}<ul class="commits">{commit_list}</ul><ul class="files">{file_list}</ul></details>
  </div>
</li>""")
    return "\n".join(rows), len(groups)


def history_tab(repo, ref, commits, admin_paths):
    era_html = []
    for era in M.ERAS:
        cs = [c for c in commits if era["from"] <= c["date"] <= era["to"]]
        keys = sum(len(c["policy"]) for c in cs)
        tasks = len({c["task"] or c["subject"] for c in cs})
        era_html.append(f"""
<li class="era">
  <div class="when">{e(era['from'][5:])} → {e(era['to'][5:])}</div>
  <div class="what">
    <h4>{e(era['name'])}</h4>
    <p>{md(era['what'])}</p>
    <p class="note"><b>Lesson</b> {e(era['lesson'])}</p>
    <p class="stats"><span>{len(cs)} process commits</span><span>{tasks} tasks</span><span>{keys} policy key changes</span></p>
  </div>
</li>""")
    # Size of the policy file over time, sampled at the end of each era.
    keys_rows, code_rows = [], []
    for era in M.ERAS:
        rev = git(repo, "rev-list", "-1", f"--before={era['to']} 23:59", ref).strip()
        keys_rows.append((era["name"], len(policy_at(repo, rev)) if rev else 0))
        try:
            code_rows.append((era["name"], prod_lines(repo, rev)))
        except subprocess.CalledProcessError:
            code_rows.append((era["name"], 0))
    bar_html = bar_rows(keys_rows)
    code_html = bar_rows(code_rows)
    log_html, n_tasks = tracker(commits)
    return f"""
<section>
  <header>
    <h2>How the flow evolved</h2>
    <p class="lede">From written rules in August, to an event-driven automation in October, and back to a lean flow. The eras are the writer's reading of the git log; the counts are computed from it.</p>
  </header>
  <ol class="eras">{''.join(era_html)}</ol>
</section>
<section>
  <header><h3>Policy size at the end of each era</h3><p class="lede">Number of keys in <code>.codex/workflow-policy.toml</code>. It did not exist before Flow V2.</p></header>
  <div class="bars">{bar_html}</div>
</section>
<section>
  <header><h3>Process code at the end of each era</h3><p class="lede">Lines of production Python in <code>scripts/workflow/</code>, tests excluded, counted the way the repository's own validator counts them.</p></header>
  <div class="bars">{code_html}</div>
</section>
<section id="changes">
  <header class="tracker-head">
    <div>
      <h3>Process change log</h3>
      <p class="lede">Only changes to how the work is done: rules, automation, scripts, process docs. No game changes. {n_tasks} tasks, {len(commits)} commits.</p>
      {tech([f"Process paths: {chips(admin_paths)}", f"Excluded because they record game work: {chips(sorted(NOT_ADMIN))}"])}
    </div>
    <label for="q"><span class="eyebrow">Search</span><br><input id="q" type="search" placeholder="e.g. runner, QC, playtest"></label>
  </header>
  <ol class="log" id="log">{log_html}</ol>
</section>"""


# ---------- assemble ----------

def build(repo, ref, out, standalone):
    now = tomllib.loads(git(repo, "show", f"{ref}:{POLICY}"))
    old = tomllib.loads(git(repo, "show", f"{M.ARCHIVE_REF}:{POLICY}"))
    head = git(repo, "rev-parse", ref).strip()
    head_date = git(repo, "log", "-1", "--format=%ad", "--date=short", ref).strip()
    prefixes = old["admission"]["protected_prefixes"] + now.get("contract", {}).get("governance_prefixes", [])
    admin_paths = sorted({p for p in prefixes if p not in NOT_ADMIN})
    commits = admin_history(repo, ref, admin_paths)
    slug = os.environ.get("FLOW_REPO", "Mozar-Team/factory-that-builds-itself")
    canary = canary_status(slug, Path(old.get("automation", {}).get("event_workflow", "x")).name)
    lanes = old["routing"]["lanes"]
    mapping = "".join(f"<tr><td>{e(M.CATEGORY_LABELS.get(k, k))}</td><td>{e(M.REVIEWER_LABELS.get(v, v))}</td></tr>"
                      for k, v in old["reviewer_mapping"].items())
    repl = {
        "{{HEAD}}": head[:7], "{{HEAD_FULL}}": head, "{{HEAD_DATE}}": head_date,
        "{{BUILT}}": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "{{ARCHIVE_NOTE}}": e(M.ARCHIVE_NOTE),
        "{{CURRENT}}": current_tab(now),
        "{{DEFAULT_LANE}}": old["default_lane"],
        "{{LANE_TABS}}": "".join(f'<button type="button" class="tab" data-lane-tab="{l}" aria-pressed="{str(l == old["default_lane"]).lower()}">{l}</button>' for l in lanes),
        "{{LANES}}": "".join(lane_section(old, l) for l in lanes),
        "{{AUTOMATION}}": automation_section(old, canary),
        "{{UNKNOWN}}": "",
        "{{REPAIR_LIMIT}}": str(old["repair"]["limit"]), "{{STOP_STATUS}}": e(old["repair"]["stop_status"]),
        "{{WRITER_PAR}}": str(old["writer_parallelism"]),
        "{{FORCED}}": chips(old["routing"]["forced_elevated_categories"], M.CATEGORY_LABELS),
        "{{ARCH_CATS}}": chips(old["routing"]["architect_required_categories"], M.CATEGORY_LABELS),
        "{{PROTECTED}}": chips(old["admission"]["protected_prefixes"]),
        "{{MAPPING}}": mapping, "{{QC_FIELDS}}": chips(old["products"]["qc_comment_fields"]),
        "{{V3}}": v3_tab(), "{{GOVERNANCE}}": governance_tab(now),
        "{{HISTORY}}": history_tab(repo, ref, commits, admin_paths),
    }
    page = (HERE / "template.html").read_text()
    for k, v in repl.items():
        page = page.replace(k, v)
    if standalone:
        page = '<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n' + page.replace("<main", "</head><body><main", 1) + "</body></html>\n"
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(page)
    print(f"{out}: {len(commits)} process commits, policy schema {now['schema_version']} @ {head[:7]}, canary {'unread' if canary is None else canary.get('when')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--out", default=str(HERE / "docs" / "index.html"))
    ap.add_argument("--standalone", action="store_true", help="wrap in a full HTML document")
    a = ap.parse_args()
    build(a.repo, a.ref, a.out, a.standalone)

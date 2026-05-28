# Graph query recipes — reference

Copy-paste lookups against the local graph. These are the *how* behind the sketches in
[`../SKILL.md`](../SKILL.md); for what the nodes/edges mean, see
[`graph-schema.md`](graph-schema.md).

All recipes are **read-only** and **stdlib-only**. Run them with `python` from the repo root.
They print plain lines so an agent can read the result straight from the transcript.

## The loader (paste this first)

Every recipe starts from a list of edges. `load_edges()` prefers the shipped helper
(`scripts/graph.py` → `read_graph()`, which unions + de-dupes every session file) and falls
back to reading the JSON directly, so it works even outside the plugin context. It honours
`BACKLOGD_GRAPH_DIR` either way.

```python
import os, sys, glob, json
from collections import defaultdict

def load_edges():
    """All edges from the local graph store (read-only, best-effort)."""
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if root:
        sys.path.insert(0, os.path.join(root, "scripts"))
        try:
            import graph
            return graph.read_graph()
        except Exception:
            pass  # fall through to direct read
    graph_dir = os.environ.get("BACKLOGD_GRAPH_DIR") or os.path.join(".backlogd", "graph")
    edges, seen = [], set()
    for path in sorted(glob.glob(os.path.join(graph_dir, "*.json"))):
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception:
            continue  # skip missing/garbage files — never raise
        for e in (data if isinstance(data, list) else []):
            if isinstance(e, dict):
                key = (e.get("src"), e.get("tgt"), e.get("type"), e.get("session"))
                if key not in seen:
                    seen.add(key)
                    edges.append(e)
    return edges

def _file(node):     # "module:scripts/x.py" -> "scripts/x.py"
    return node[len("module:"):] if node.startswith("module:") else node

def _problem(node):  # "problem:linear:NB-9" -> "NB-9"
    return node[len("problem:linear:"):] if node.startswith("problem:linear:") else node
```

> **Note.** Recipes 1–3 query the *legacy* file-edge dimension (`touches` /
> `solves`). New runs no longer emit `touches`, so on a fresh graph these will return
> nothing — they keep working against historical data. For the primary signal of the
> graph (agent-execution metrics), skip to recipe 4 or run `graph.py report`.

## 1. problem-history — *which files did problem X touch?* (legacy / low-signal)

> Sessions that solved X (either `solves` or `dispatch_completed`) → modules those
> sessions `touches`.

```python
PROBLEM = "NB-241"   # <- the Linear identifier

edges      = load_edges()
target     = f"problem:linear:{PROBLEM}"
solve_like = {"solves", "dispatch_completed"}
sessions   = {e["src"] for e in edges if e["type"] in solve_like and e["tgt"] == target}
files      = sorted({_file(e["tgt"]) for e in edges
                     if e["type"] == "touches" and e["src"] in sessions})

if not files:
    print(f"No recorded files for {PROBLEM} (graph may be empty or new-flow only).")
else:
    print(f"Files touched while solving {PROBLEM}:")
    for f in files:
        print(f"  {f}")
```

## 2. module-history — *which problems touched file Y?* (legacy / low-signal)

> Sessions that `touches` Y → problems those sessions solved (either `solves` or
> `dispatch_completed`).

```python
MODULE = "scripts/graph.py"   # <- repo-relative path (forward slashes)

edges      = load_edges()
target     = f"module:{MODULE}"
solve_like = {"solves", "dispatch_completed"}
sessions   = {e["src"] for e in edges if e["type"] == "touches" and e["tgt"] == target}
problems   = sorted({_problem(e["tgt"]) for e in edges
                     if e["type"] in solve_like and e["src"] in sessions})

if not problems:
    print(f"No recorded problems for {MODULE} (graph may be empty or new-flow only).")
else:
    print(f"Problems whose sessions touched {MODULE}:")
    for p in problems:
        print(f"  {p}")
```

## 3. find-similar — *which past problems share a touch-set with problem X?* (legacy / low-signal)

> Build each problem's touch-set (the union of files its solving sessions touched), then rank
> every *other* problem by overlap with X's set. Sorted by Jaccard similarity, then shared
> count.

```python
PROBLEM = "NB-264"   # <- the problem to find neighbours of

edges = load_edges()
solve_like = {"solves", "dispatch_completed"}

# session -> its touched modules, and session -> its solved problems
sess_modules  = defaultdict(set)
sess_problems = defaultdict(set)
for e in edges:
    if e["type"] == "touches":
        sess_modules[e["src"]].add(e["tgt"])
    elif e["type"] in solve_like:
        sess_problems[e["src"]].add(e["tgt"])

# problem -> union of modules across the sessions that solved it
prob_modules = defaultdict(set)
for s, probs in sess_problems.items():
    for p in probs:
        prob_modules[p] |= sess_modules[s]

target  = f"problem:linear:{PROBLEM}"
tset    = prob_modules.get(target, set())
ranked  = []
for p, mods in prob_modules.items():
    if p == target or not (tset & mods):
        continue
    shared  = tset & mods
    jaccard = len(shared) / len(tset | mods)
    ranked.append((jaccard, len(shared), _problem(p), sorted(_file(m) for m in shared)))

if not ranked:
    print(f"No problems share a touch-set with {PROBLEM}.")
else:
    print(f"Problems most similar to {PROBLEM} (by shared files):")
    for jac, n, p, shared in sorted(ranked, reverse=True):
        print(f"  {p}  jaccard={jac:.2f}  shared={n}: {', '.join(shared)}")
```

## 4. agent-execution metrics — *how is the loop performing?*

> The primary signal of the graph. For the rolled-up view (rework rate, partial rate,
> p50/p90 dispatch→PR latency, blocker frequency by `area:*`), use the CLI directly:

```bash
python scripts/graph.py report           # markdown table
python scripts/graph.py report --json    # the raw metrics dict
```

Need a slice of the data the report doesn't expose? Read it inline with the same loader
above and filter on `type`:

```python
edges = load_edges()

# Per-outcome counts
from collections import Counter
outcomes = Counter(e.get("outcome") for e in edges if e["type"] == "dispatch_completed")
print(outcomes)  # Counter({'solved': 12, 'blocked': 3, 'partial': 1})

# Slowest dispatches (descending latency_ms)
slow = sorted(
    (e for e in edges if e["type"] == "dispatch_completed" and e.get("latency_ms")),
    key=lambda e: -e["latency_ms"],
)[:5]
for e in slow:
    print(f"  {_problem(e['tgt'])}: {e['latency_ms']/1000:.1f}s ({e.get('outcome')})")

# Problems that have come back from review
rework = {_problem(e["tgt"]) for e in edges if e["type"] == "rework"}
```

The full list of agent-execution edge types and their extra fields is in
[`graph-schema.md`](graph-schema.md) → "Agent-execution edges".

## Notes

- **Empty results are normal**, not errors — the store is gitignored and may be absent or
  sparse. Every recipe prints a "nothing found" line and exits cleanly.
- **One-liner form.** For a quick check you can inline a recipe:
  `python -c "import sys; sys.argv=['']; exec(open('…').read())"` is overkill — prefer pasting
  the loader + the lookup into a `python - <<'PY' … PY` heredoc.
- **Resolve details in Linear.** A lookup returns `NB-N` ids and file paths only. To get a
  problem's title/status, read it in Linear via the MCP (see the `linear` skill) — keep the
  graph query itself offline.
- **Programmatic counterparts.** Most of the logic is exposed as CLI subcommands on
  `scripts/graph.py`:
  - **Reads:** `prior-work --problem NB-N` (Prior work block, problem-history + find-similar);
    `report` (markdown table of agent-execution metrics); `report --json` (raw dict).
  - **Agent-execution writes (orchestrator-only):** `dispatch-start`, `dispatch-end --outcome`,
    `pr-opened`, `run-end`, `rework --notes "…"`, `labeled --labels area:foo …`.
  - **Legacy write:** `emit --session S --problem NB-N --stdin` appends `solves` + `touches`
    edges from piped file paths (retained for back-compat; not used by the new loop).
  All subcommands are best-effort (always exit 0). See `skills/solve/dispatch.md`,
  `skills/solve/handoff.md`, and `commands/review.md` for how the writes wire into the loop.

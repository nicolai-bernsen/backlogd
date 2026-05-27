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

## 1. problem-history — *which files did problem X touch?*

> Answers AC: *"what files relate to problem X."* Sessions that `solves` X → modules those
> sessions `touches`.

```python
PROBLEM = "NB-241"   # <- the Linear identifier

edges    = load_edges()
target   = f"problem:linear:{PROBLEM}"
sessions = {e["src"] for e in edges if e["type"] == "solves" and e["tgt"] == target}
files    = sorted({_file(e["tgt"]) for e in edges
                   if e["type"] == "touches" and e["src"] in sessions})

if not files:
    print(f"No recorded files for {PROBLEM} (graph may be empty).")
else:
    print(f"Files touched while solving {PROBLEM}:")
    for f in files:
        print(f"  {f}")
```

## 2. module-history — *which problems touched file Y?*

> Answers AC: *"what problems touched file Y."* Sessions that `touches` Y → problems those
> sessions `solves`.

```python
MODULE = "scripts/graph.py"   # <- repo-relative path (forward slashes)

edges    = load_edges()
target   = f"module:{MODULE}"
sessions = {e["src"] for e in edges if e["type"] == "touches" and e["tgt"] == target}
problems = sorted({_problem(e["tgt"]) for e in edges
                   if e["type"] == "solves" and e["src"] in sessions})

if not problems:
    print(f"No recorded problems for {MODULE} (graph may be empty).")
else:
    print(f"Problems whose sessions touched {MODULE}:")
    for p in problems:
        print(f"  {p}")
```

## 3. find-similar — *which past problems share a touch-set with problem X?*

> Build each problem's touch-set (the union of files its solving sessions touched), then rank
> every *other* problem by overlap with X's set. Sorted by Jaccard similarity, then shared
> count.

```python
PROBLEM = "NB-264"   # <- the problem to find neighbours of

edges = load_edges()

# session -> its touched modules, and session -> its solved problems
sess_modules  = defaultdict(set)
sess_problems = defaultdict(set)
for e in edges:
    if e["type"] == "touches":
        sess_modules[e["src"]].add(e["tgt"])
    elif e["type"] == "solves":
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

## Notes

- **Empty results are normal**, not errors — the store is gitignored and may be absent or
  sparse. Every recipe prints a "nothing found" line and exits cleanly.
- **One-liner form.** For a quick check you can inline a recipe:
  `python -c "import sys; sys.argv=['']; exec(open('…').read())"` is overkill — prefer pasting
  the loader + the lookup into a `python - <<'PY' … PY` heredoc.
- **Resolve details in Linear.** A lookup returns `NB-N` ids and file paths only. To get a
  problem's title/status, read it in Linear via the MCP (see the `linear` skill) — keep the
  graph query itself offline.

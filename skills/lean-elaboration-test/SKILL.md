---
name: lean-elaboration-test
description: Run a repeatable elaboration test of one Lean 4 repository and write a dated report of source size, project-only rebuild wall time and CPU use, elapsed build-action timings, heavy tails, and warm own-file profiles. Use for repository build profiling or tracking elaboration health over time.
---

# Lean Elaboration Test

A standardized, comparable snapshot of how one repository elaborates. The
method incorporates repeated report-series corrections for partial default
targets, contention artifacts, and build-log versus own-file timing.

**Scope rule: elaborate JUST THIS REPO.** Never mathlib, never upstream
path-dependencies (their oleans are inputs, not measurands). A healthy timed
build compiles only this repo's own modules; if the log shows upstream
compilation, the run is invalid — kill it, fix the cache, restart.

The companion skill **lean-elaboration** consumes this test's findings.

## Phase 0 — Preconditions (all mandatory)

1. **Sync if asked / note the commit.** All size numbers come from git at the
   measured commit, never `find` on a working tree (mid-flight agent edits
   corrupted a baseline once): `git rev-parse HEAD`, `git status --short`.
2. **Upstream olean guards.** Count oleans for Mathlib and any dependencies
   (e.g. `find .lake/packages/mathlib/.lake/build/lib -name '*.olean' | wc -l`);
   compare against repository-documented thresholds. If no threshold exists,
   verify that required dependency artifacts are populated before a timed run.
   If artifacts are missing, stop and use only the repository-approved cache
   restoration or one-time dependency setup procedure.
3. **Process inventory is informational, never a build gate.** You may record
   `pgrep -x lake` and `ps -eo user,etime,args | grep -E "[l]ake|[l]ean "`
   (bracket trick so grep doesn't match itself) to disclose co-running load.
   Never wait, stop, or refuse the test merely because another Lean/Lake process
   exists, including one in the same checkout or an upstream checkout. Only an
   actually observed upstream compilation or build-tree mutation invalidates
   the run; process presence is not evidence of either.
4. **Read the repo's agent instructions** (olean preservation, guard hooks,
   default build target). Respect them; the test must be a no-op for
   everyone else on the machine.
5. **NEVER `lake clean`. NEVER `lake update`.**

## Phase 1 — Size snapshot

Record: **date (UTC), commit, .lean file count, total lines, non-comment code
lines, comment-only files excluded**. Use
[scripts/count_lean_lines.py](scripts/count_lean_lines.py) (self-contained;
counts from `git ls-tree` at the measured commit; a file is comment-only if
it has no non-comment, non-whitespace character — such files are excluded
from the file/line counts and listed by name). It also counts and lists
non-module files (no `module` header; `lakefile.lean` exempt). Record the
count for non-comment-only files. It is informational unless the project has
adopted the module system or a target registry requires it. In that setting,
run the architecture skill's module checker; profiling alone never requires a
module migration.

Also record what the *build root* covers if it differs from the git tree.
Quarantined/off-facade modules can make the source tree larger than the build
scope. For built size, identify unique own-repository Lean modules actually
compiled using their Lean build facet, excluding replays, repeated actions,
and native compilation jobs. Report total progress jobs separately; they are
not a Lean module count.

**Verify the default target covers what you think it covers.** A prior report
series measured partial builds because the root facade silently omitted a
large subtree. Check the root `.lean` facade's imports, or
enumerate targets explicitly.

## Phase 2 — Clean project-only rebuild (the timed run)

Use the repository's guarded project-only rebuild command when it has one.
Otherwise identify the exact library root (for example `Project`) and prepare
an explicit project-artifact invalidation plan. Confirm every resolved path is
inside this repository's own build subtree and cannot match a dependency tree
before removing anything. A generic shape is:

```bash
rm -rf .lake/build/lib/lean/<Root>
rm -f .lake/build/lib/lean/<Root>.{olean,ilean,trace,olean.hash,ilean.hash}
rm -rf .lake/build/ir/<Root>
/usr/bin/time -v <repo-approved-build-command> > <unique-log-path> 2>&1
```

Treat the snippet as a template, not authorization to delete unresolved or
broad paths. Do not use it when local instructions provide a wrapper.

Use GNU `/usr/bin/time -v` (gives %CPU and peak RSS; bash `time` doesn't).
Note the tool in the report — cross-tool CPU splits aren't comparable.

**Watch the first minutes**: any `.lake/packages/mathlib` compile lines, or
bulk upstream-module compiles → kill immediately, diagnose, do not let it
run.

Record from `/usr/bin/time -v` + the log:
- exit status, error count, `sorry` count (vs authorized list), warning count
- wall-clock (Elapsed), user CPU, sys CPU, %CPU, peak RSS
- total jobs (`[N/M]` progress lines), and confirm only own-repo modules
  compiled

## Phase 3 — Per-file extraction from the build log

```bash
python3 scripts/parse_build_timings.py <log> --root-module <Root>
```

Use the bundled [scripts/parse_build_timings.py](scripts/parse_build_timings.py)
from the installed skill path, or copy it to the target repository. Repeat
`--root-module` for each project library. It accepts seconds and milliseconds,
strips ANSI formatting, preserves optional/repeated build actions and facet suffixes,
and counts actions with no timing separately. Check its root filters against
the actual captions in the pinned Lake version; an empty match is an error.

- **Measured CPU** = user CPU + system CPU from the timed build process tree.
  **CPU utilization in core equivalents** = measured CPU ÷ elapsed wall-clock.
  This measures average CPU use, not configured job concurrency.
- **Sum of logged build-action elapsed times** = Σ of parsed `Built` durations.
  Lake uses a monotonic clock for these durations; their sum is not CPU time.
  Report timed/untimed action counts, target/facet scope, and repeated actions.
  This sum is diagnostic; it does not measure CPU utilization or establish
  complete build coverage. Progress counters may also include cache replays
  and non-Lean jobs.
- **Per-line CPU cost** = measured CPU ÷ code lines (ms/line), with the measured
  source/build scope stated. Keep summed elapsed time per line separately
  labeled if it is useful.
- **Heavy-tail tiers**: file counts ≥10s / ≥20s / ≥30s / ≥40s (the policy
  thresholds to track when comparable targets and conditions are available).
- **Top-30 worst files**, annotated `vs <prior report date>` where a prior
  snapshot exists. State which Lean facet supplies each file timing; do not
  count native compilation facets or repeated actions as distinct Lean files.
- **Per-namespace / per-directory aggregation** of logged elapsed times with
  Δ vs prior — this locates slow groups, without claiming per-namespace CPU.

Lake's timing and display implementations are in
[Common.lean](https://github.com/leanprover/lean4/blob/master/src/lake/Lake/Build/Common.lean)
and [Run.lean](https://github.com/leanprover/lean4/blob/master/src/lake/Lake/Build/Run.lean).
Check the project's pinned version when its output differs.

## Phase 4 — Warm own-file profiling of the worst files

Build wall-clock ≠ own-file cost (includes upstream rebuilds, olean/IR
writes, contention; ~25–40% inflated under parallel load, 2.5× observed).
Confirm each candidate **serially, after the build, one at a time**:

```bash
<repo-approved-lean-command> --profile <Root>/<Path>/File.lean 2>&1 | tail -25
```

For the top 5–10 files record wall + the `cumulative profiling times` block
(typeclass inference / simp / elaboration / interpretation:<tactic> /
import / tactic execution / type checking), events >100ms. Classify each
file's dominant phase and likely cause:
- `import`-dominated → not a local problem; candidate is upstream or the
  file's import list.
- `interpretation:nlinarith`/`linarith` → arithmetic-closer elimination.
- `typeclass inference`, few large events → head-class cache candidate (name
  the searched class! e.g. eight ~1s `SMul` searches = one missing cache).
- `typeclass inference`, thousands of sub-100ms events → diffuse floor;
  don't promise a fix.
- large unattributed `elaboration` → rerun with
  `-D trace.profiler.output=out.json` for per-declaration attribution before
  claiming a cause.

## Phase 5 — Trend comparison (when prior reports exist)

- Compare wall-clock under matched job settings, hardware, target, toolchain,
  cache state, and timing tool. Otherwise report measured CPU and summed
  elapsed action times separately, with their comparability limits. CPU
  utilization alone does not establish matched scheduling conditions.
- Contention artifact check before believing any regression: (a) user CPU
  down while logged elapsed-sum rises? (b) job settings or CPU utilization
  changed? (c) same-file timings
  moving in opposite directions? Any two → report the run as
  contention-bound and skip structural conclusions.
- Predicted-vs-actual: Δlines × prior measured CPU ms/line vs actual ΔCPU.
  Big ratios (>2×) are prompts to investigate changed targets, downstream
  load, or a regression; they do not establish a cause.
- Flag any single file on a monotonic climb across ≥3 reports.

## Phase 6 — The report

Write `ELABORATION_REPORT_<YYYY-MM-DD>.md` (or the repo's established
naming) at the repo root. Sections, in order:

1. **Setup/provenance** — date-time window, commit, host, tool, exact
   commands, co-running load observed, which build target.
2. **Size snapshot** — files, lines, non-comment lines, comment-only files
   excluded, built-vs-tree scope note.
3. **Headline table** — wall, user/sys CPU, %CPU, CPU core equivalents,
   configured job settings, peak RSS, action counts, summed logged elapsed
   time, and per-line CPU ms; prior snapshots with comparability caveats.
4. **Build health** — exit status, errors, sorries vs authorized, warning
   census (top kinds), rule compliance (no upstream compiles, file-size
   limits, heartbeat overrides).
5. **Heavy tail** — tier table (≥10/20/30/40s) with Δ vs prior; top-30 files.
6. **Per-namespace logged elapsed times** with Δ vs prior.
7. **Own-file profiles** of the worst files — the phase table, dominant
   category per file.
8. **Findings ranked by actionability** — each with the evidence, the named
   lever (per the lean-elaboration skill), and expected value; separate
   "measurement only, no fix applied" honestly.
9. **What is NOT established** — unattributed time, unprofiled tails,
   contention limits. Every number a future reader might over-trust gets a
   caveat here.
10. **Methodology** — commands verbatim, so the next run is identical.
11. **Pointers** — prior reports with their roles (last clean baseline, peak
    regression, etc.).

## Cost & etiquette notes

- The timed rebuild can be expensive. Estimate from the repository's prior
  reports when available; on a shared machine, warn before
  running. Other agents' builds may run concurrently; record the load and mark
  timing comparisons contention-bound when appropriate, but do not delay the
  measurement merely because another build exists.
- Profiling (Phase 4) is cheap (~10–60s/file) but must be serial.
- If the measured artifact tree changes concurrently, report clearly that the
  numbers are contaminated; do not infer contamination from a process listing.
- The report is measurement; applying fixes is the lean-elaboration skill's
  loop with per-change A/B — do not mix the two in one pass.

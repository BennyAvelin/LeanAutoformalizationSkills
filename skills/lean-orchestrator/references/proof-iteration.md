# Develop, review, and integrate

Keep ordinary proof iteration separate from certification, within the target
repository's build, ownership, and integrity requirements. Changes to additional
campaign procedures must be adopted explicitly rather than silently bypassed.

- **Develop:** use a stable scratch Lake environment with separate source
  ownership and cached dependencies. Use available Lean diagnostics, goals,
  and tactic attempts, or narrow Lean/Lake checks. Send failures directly to
  the owning writer. Routine edits and failed tactics need no closure manifest,
  release packet, full snapshot, or independent runner review unless an
  applicable project rule requires one. Protect frozen declarations and
  accepted sources. Scratch work has no certification status or proof count.
- **Review:** once a bounded result and its real importing consumer work,
  freeze the completed packet for independent review. Check exact source
  fidelity, expanded binders and definitions, shared witnesses and constants,
  actual predecessor consumption, the complete conclusion, and axiom closure.
  If reviewed inputs change, invalidate the affected evidence and review the
  successor. Retain earlier attempts without duplicating unchanged context.
- **Integrate:** use one controlled landing and the required integration checks.
  Record a concise closure manifest linking exact input identities, commands,
  complete logs and results, independent review, axiom evidence, and the
  node/root status transition. That manifest organizes the obligations; it
  does not replace any of them or promote a helper to a proved source node.

Prefer a reusable validation driver to manually assembled runner packets when
repeated checks justify it. Reuse successful evidence only while all relevant
source, dependency, imported-object, toolchain/configuration, and review-context
identities remain valid. Check changed modules and affected consumers; retain
required combined builds, independent applications, and fresh cache/integrity
guards. Within one invocation, hash each unique file once and compare its
digest with every expected binding. Reuse across invocations requires verified
identity evidence.

Generate current status and required reporting fields from authoritative
registries. Preserve historical checkpoints and distinguish source-node, root,
citation, and implementation counts. Report import-root coverage separately
from actual compilation. A held module needs an explicit ownership/status
entry; absence from production imports does not prove it is uncompiled.

Keep work in progress bounded by validated interfaces and review capacity.
Release dependent tasks only after their prerequisites are sealed, independently
audited, and available under the campaign's dependency policy, and their real
consumer checks pass. Parallelize independent ready obligations. Measure
repeated checks, environment failures, and review waiting time before adding
process machinery.

# Finding timing: must-fix-now vs defer (shared Security + QA rubric)

> Both **Stage-4 Security (Shreya)** and **Stage-5 QA (Tanvi)** classify a finding's *timing* with this **one** rubric, so the two gates converge instead of diverging on the same issue (the O7 bounce class — Child 1: Shreya said `defer`, Tanvi said `blocking` on the same finding → a costly reconciliation bounce). Severity (CRIT/HIGH/MED/LOW) is a separate axis; this is **now-vs-defer** only.

A finding is **MUST-FIX-NOW (blocks this requirement)** if **ANY**:
- it is a correctness / safety / security / compliance / tenant-isolation / data-loss / money-correctness defect reachable in the code **this requirement ships**;
- it breaks a **day-one invariant** (workspace_id 4-layer, minor-units money, Decision Log, traceability, RLS fail-closed, idempotency);
- it is a **"must-fix-before-X"** gap where X happens **within this requirement or as its direct consequence** (e.g. must-fix-before-FORCE when FORCE ships in this slice).

A finding is **SAFE-TO-DEFER (track to a later child / backlog)** only if **ALL**:
- it manifests only in a **future** slice/step **not shipped here**; AND
- there is a **named owner + a hard gate** before that future step; AND
- it is **not** a security / compliance / data-loss / money defect in the current code.

**Conservative tie-break (non-negotiable):** on **any** disagreement or doubt between now-vs-defer, classify **MUST-FIX-NOW**. (Mirrors the lane tie-break: a deferred-that-should've-been-fixed is a production risk; a fixed-that-could've-deferred costs a little extra work. The asymmetry is the point.) Record the classification + which clause fired in your review artifact.

> **Upstream (prevents the bounce entirely):** the **architect** folds known `must-fix-now` concerns into the **builder's acceptance contract** (so they're built in pass 1), and the **builder** self-reviews against these gate criteria before handoff (system-prompt §11 shift-left). This rubric is the **gate-side backstop** for anything that slipped through — applied identically by both gates so they don't bounce on a classification mismatch.

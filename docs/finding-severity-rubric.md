# Finding timing: must-fix-now vs defer (shared Security + QA rubric)

> Both **Stage-4 Security** and **Stage-5 QA** classify a finding's *timing* with this **one** rubric, so the two gates converge instead of diverging on the same issue (a costly reconciliation bounce: one reviewer says `defer`, the other says `blocking` on the same finding). Severity (CRIT/HIGH/MED/LOW) is a separate axis; this is **now-vs-defer** only.

A finding is **MUST-FIX-NOW (blocks this requirement)** if **ANY**:
- it is a correctness / safety / security / compliance / tenant-isolation / data-loss / money-correctness defect reachable in the code **this requirement ships**;
- it breaks a **day-one invariant** (tenant-isolation enforced at every layer, minor-units money, the system-of-record audit log, traceability, isolation fail-closed, idempotency);
- it is a **"must-fix-before-X"** gap where X happens **within this requirement or as its direct consequence** (e.g. must-fix-before-FORCE when FORCE ships in this slice).

A finding is **SAFE-TO-DEFER (track to a later child / backlog)** only if **ALL**:
- it manifests only in a **future** slice/step **not shipped here**; AND
- there is a **named owner + a hard gate** before that future step; AND
- it is **not** a security / compliance / data-loss / money defect in the current code.

**Conservative tie-break (non-negotiable):** on **any** disagreement or doubt between now-vs-defer, classify **MUST-FIX-NOW**. (Mirrors the lane tie-break: a deferred-that-should've-been-fixed is a production risk; a fixed-that-could've-deferred costs a little extra work. The asymmetry is the point.) Record the classification + which clause fired in your review artifact.

> **Upstream (prevents the bounce entirely):** the **Architect** folds known `must-fix-now` concerns into the **builder's acceptance contract** (so they're built in pass 1), and the **builder** self-reviews against these gate criteria before handoff (shift-left). This rubric is the **gate-side backstop** for anything that slipped through — applied identically by both gates so they don't bounce on a classification mismatch.

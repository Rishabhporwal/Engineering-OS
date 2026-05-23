---
name: data-residency-enforcement
description: How India-in-region (ap-south-1) is STRUCTURALLY enforced + CONTINUOUSLY tested, not just configured. IaC guardrails / SCPs that prevent cross-region data writes; a test that PROVES an Indian workspace's data physically cannot land outside ap-south-1; per-region routing keyed off the workspace home_region; KSA/UAE residency + SDAIA-approved transfer mechanisms (SCCs/BCRs) for Phase-4 GCC. Residency is a DEFAULT, not enterprise-only (DPDP + KSA PDPL transfer restrictions). Use when provisioning infra, adding a region, routing a workspace's storage, or reviewing any cross-region data path. Owner: Jatin + Shreya.
---

# Data-residency enforcement — structural, not a config flag

Canon says "Indian customer data is stored in-region (ap-south-1) **by default**" (TECH/16 §4.3, TECH/09 §5). The risk: residency that is merely *configured* (a region picked at deploy) silently breaks the day someone adds a cross-region S3 replication rule, a global DynamoDB table, or a backup to us-east-1. DPDP and KSA PDPL impose **transfer restrictions** — a leak across the region boundary is a compliance violation, not a perf bug. This skill makes residency a **guardrail that physically blocks** the wrong write, plus a **test that proves** the block holds.

> **The one rule:** *an Indian workspace's data physically cannot be written, replicated, or backed up outside ap-south-1 — and we have a test that fails CI if that ever becomes possible.* Residency is the default for every workspace, not an enterprise upsell.

**Canonical source:** TECH/16 §4.3 (residency default) + §6 (residency test gate), TECH/09 §5 (per-region Supabase/ClickHouse/MSK), resolutions R8/R9. Owned by **Jatin** (infra/IaC) + **Shreya** (compliance VETO). Brain uses **AWS CDK** (not Terraform).

## 1. IaC guardrails + SCPs — prevent the wrong write structurally

Configuration alone is bypassable; **Service Control Policies (SCPs)** at the AWS Organizations level and CDK Aspects at synth time make cross-region data placement impossible to deploy.

```jsonc
// SCP on the prod OU — deny creating/writing data stores outside the allowed regions
{ "Effect": "Deny",
  "Action": ["s3:PutObject","rds:CreateDBInstance","dynamodb:CreateTable",
             "kafka:CreateCluster","es:CreateDomain"],
  "Resource": "*",
  "Condition": { "StringNotEquals": { "aws:RequestedRegion": ["ap-south-1"] } } }
// Phase 4: add me-central-1 (UAE) / the KSA region per the workspace's allowed set.
```

```typescript
// infra/cdk — an Aspect that fails `cdk synth` if any data resource lands off-region
class ResidencyAspect implements cdk.IAspect {
  visit(node: IConstruct) {
    if (isDataStore(node) && node.stack.region !== 'ap-south-1' /* + allowed GCC regions */) {
      Annotations.of(node).addError(`Residency: ${node.node.path} not in an allowed region`);
    }
  }
}
```

Also denied/guarded: **S3 cross-region replication** rules targeting a non-allowed region, **RDS/Aurora cross-region snapshots**, **DynamoDB global tables**, **AMI/EBS snapshot copies**, and **CloudWatch/OpenSearch log shipping** to another region (logs carry `workspace_id` + redacted PII — they're in scope too). `cdk-nag` (already in `vulnerability-scanning`) carries a custom rule for this.

## 2. Per-region routing keyed off `home_region`

Every workspace has a read-only `home_region` (set at creation, immutable — same rule as `region-adapter`). A workspace's storage is resolved from it, never assumed:

```python
# Storage targets resolve from the workspace's home_region — never a hardcoded endpoint
def stores_for(workspace) -> StorageTargets:
    region = RESIDENCY_REGION[workspace.home_region]   # IN→ap-south-1, AE→me-central-1, SA→ksa (Phase 4)
    return StorageTargets(
        pg = supabase_project(region),    # per-region Supabase project
        ch = clickhouse_cluster(region),  # per-region ClickHouse cluster
        msk = msk_cluster(region),        # per-region MSK
        s3 = bucket(region))              # per-region bucket prefix
```

This is the data-plane mirror of `RegionAdapter` resolution: behaviour varies by region behind an interface, and `workspace_id` (which carries `home_region`) is already on every row/event/cache-key/log, so routing has the key it needs everywhere. Phase 0–1 single-region (ap-south-1 only) is fine — the **routing seam exists now** so Phase 4 GCC is additive, not a migration.

## 3. The test that PROVES it (TECH/16 §6 residency gate)

A configured guardrail you never test is a hope. The compliance test matrix has a residency assertion — implement it as a real, failing-if-violated test:

```python
# Compliance test (Tanvi/QA VETO gate) — TECH/16 §6 "Residency"
def test_indian_workspace_data_never_leaves_ap_south_1():
    ws = make_workspace(home_region='IN')
    write_order(ws, sample_order())
    # 1. Routing: every resolved store endpoint is ap-south-1
    t = stores_for(ws)
    assert all(region_of(e) == 'ap-south-1' for e in (t.pg, t.ch, t.msk, t.s3))
    # 2. Negative: attempting an off-region write is DENIED, not silently allowed
    with pytest.raises(AccessDenied):
        s3_client('us-east-1').put_object(Bucket=t.s3.replace('ap-south-1','us-east-1'), ...)
    # 3. No replication/global-table config exists that would copy this ws's data off-region
    assert no_cross_region_replication(t.s3) and no_global_tables_touching(ws)
```

Run it in CI + as a periodic production conformance check (continuously tested, not once at launch). Pair with an **AWS Config rule** / scheduled audit that flags any data resource or replication rule outside the allowed set — drift detection between deploys.

## 4. KSA / UAE residency + transfer mechanisms (Phase 4)

GCC has its own — stricter — transfer regime:

- **KSA PDPL** (enforced 14 Sep 2024, regulated by **SDAIA**): cross-border transfer of personal data is restricted; transfers out require an **adequacy decision, SDAIA-approved appropriate safeguards (SCCs/BCRs), or a narrow exception**. KSA workspace data lands in the KSA region; transfers out only via an approved mechanism logged in the DPA.
- **UAE PDPL** (Federal Decree-Law 45/2021): cross-border transfer permitted to adequate jurisdictions or under appropriate safeguards (contractual clauses / BCRs). UAE workspace data in the UAE region (me-central-1).
- The SCP allowed-region set expands per-workspace to the workspace's region; **a KSA workspace's SCP never permits ap-south-1**, and vice-versa — isolation runs both ways.
- Sub-processors (Supabase, ClickHouse Cloud, Anthropic, gateways) must have a per-region presence or an approved transfer basis recorded in the sub-processor list (TECH/16 §8 Q5) before a GCC brand goes live.

DPDP (India) likewise permits transfers except to government-blacklisted countries; Brain's posture is **store-in-region by default** and treat any cross-region flow as an explicit, logged, mechanism-backed exception — never an accident.

## Anti-patterns (code-review blockers / Shreya VETO)

- **S3 cross-region replication / RDS cross-region snapshot / DynamoDB global table / AMI copy** that moves an Indian (or KSA/UAE) workspace's data off its region.
- **Hardcoded storage endpoints** instead of resolving from `home_region` — the leak `region-adapter` forbids, applied to the data plane.
- **Logs/backups shipped cross-region** (they carry `workspace_id` + PII) — in scope, same rule.
- Residency offered **only to enterprise** workspaces — it's the default for every workspace (DPDP/PDPL).
- A residency claim with **no SCP and no residency test** — config without a guardrail and a proof.
- A Phase-4 GCC cross-border transfer with **no SCC/BCR / SDAIA-approved basis** logged.

## Verify

- `cdk synth` fails if any data store / replication rule targets a non-allowed region (ResidencyAspect + cdk-nag).
- `test_indian_workspace_data_never_leaves_ap_south_1` passes (routing + denied off-region write + no replication).
- AWS Config / scheduled audit reports zero data resources outside the allowed region set.
- A stub KSA workspace routes to the KSA region and its SCP refuses ap-south-1.

## References
- TECH/16 §4.3 (residency default) + §6 (residency test) + §8 Q5 (sub-processors)
- TECH/09 §5 (per-region Supabase/ClickHouse/MSK, multi-region residency)
- [`region-adapter`](../region-adapter/SKILL.md) — `home_region` resolution + the no-fork rule
- [`data-privacy-dpdp`](../data-privacy-dpdp/SKILL.md) — DPDP/PDPL transfer restrictions + erasure
- [`devops-aws`](../devops-aws/SKILL.md) — CDK, SCPs, cdk-nag, per-region infra
- [`multi-tenancy-isolation`](../multi-tenancy-isolation/SKILL.md) — `workspace_id` carries `home_region` everywhere

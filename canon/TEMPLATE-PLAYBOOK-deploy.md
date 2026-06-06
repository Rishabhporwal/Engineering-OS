# PLAYBOOK — deploy (TEMPLATE)

> Copy to `.engineering-os/knowledge-base/PLAYBOOK-deploy.md`. The exact rollout/bake/rollback
> procedure + thresholds for this product. Owner: Platform/SRE. See
> `engineering-os-blueprint/07-operations-and-reliability.md §1`.

## Strategy
- **Rollout:** `<canary % steps → wider → full; or blue-green; or …>`
- **Feature flags:** `<which changes ship dark; kill-switch mechanism + latency>`
- **Artifact promotion:** `<build-once, promote the same artifact across envs>`

## Bake window
- **Duration:** `<e.g. 48h>` per `<step / overall>`
- **Watched signals (SLOs):** `<latency, error rate, saturation, the product's key correctness signal>`

## Auto-rollback
- **Trigger thresholds:** `<signal X crosses Y for Z minutes → auto-rollback>`
- **Rollback mechanism:** `<how; verified reversible; DB migrations staged so prev version runs>`
- **Post-rollback:** `<who is notified; incident opened if SEV≥?>`

## Release channels
- `<e.g. services via CD; mobile via store/OTA rules; which changes need review>`

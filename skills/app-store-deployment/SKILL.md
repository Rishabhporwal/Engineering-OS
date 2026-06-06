---
name: app-store-deployment
description: Mobile release pipeline — EAS Build → TestFlight/Play Internal → Stakeholder approval → EAS Submit; EAS Update for OTA JS-only; native bumps go to review.
---

# App Store Deployment

> **Reference implementation.** This skill documents one concrete binding of a seam (see `engineering-os-blueprint/09-reference-architecture.md`). The OS is stack-agnostic — your product's `STACK.md` may bind the mobile-release seam to different technology. The *patterns* here (OTA-vs-native split, manual production gate, post-release watch) are what transfer, not the EAS/Expo vendor.

This binding ships mobile via **EAS Build + EAS Submit + EAS Update** (Expo's managed pipeline). Native `xcodebuild`/`gradle` is hidden behind EAS. Releases go: **dev → preview → TestFlight + Play Internal → manual Stakeholder approval → production rollout**. OTA (EAS Update) ships JS-only fixes in hours, bypassing store review.

## Why this matters

- For a mobile-first product, the primary surface depends on a working binary.
- OTA is the fast path (JS-only fix in ~1h vs 1–7d store review); native changes (new permission/module, SDK upgrade) are the slow path.
- When EAS is the bound stack, there is no raw `xcodebuild`/`gradle`; the team standardizes on the `eas` CLI.

## EAS profiles (example)

```jsonc
// apps/mobile/eas.json
{
  "cli": { "version": ">= 13.0.0" },
  "build": {
    "development": { "developmentClient": true, "distribution": "internal", "channel": "development",
                     "ios": { "simulator": true }, "env": { "EXPO_PUBLIC_API_URL": "http://localhost:4000" } },
    "preview":     { "distribution": "internal", "channel": "preview",
                     "env": { "EXPO_PUBLIC_API_URL": "https://staging.api.example.com" } },
    "production":  { "channel": "production", "autoIncrement": "buildNumber",
                     "env": { "EXPO_PUBLIC_API_URL": "https://api.example.com" } }
  },
  "submit": {
    "production": {
      "ios":     { "appleId": "release@example.com", "ascAppId": "...", "appleTeamId": "..." },
      "android": { "serviceAccountKeyPath": "./play-service-account.json", "track": "production" }
    }
  }
}
```
`channel` is the EAS Update channel — a build pulls OTAs only from its own channel.

## OTA vs store review — the decision tree

```
Is the change JS-only?
  (no native module added/removed, no permission added, no SDK upgrade,
   no Info.plist/AndroidManifest/app.json native field change)
   ├─ YES → EAS Update (1–2h):  eas update --branch production --message "fix: handle null delta"
   └─ NO  → full native build + store review (1–7d):
            eas build --platform all --profile production → TestFlight + Play Internal
            → Stakeholder manual approval → eas submit --platform all --profile production
            → review (Apple 1–3d, Google hours–1d) → production rollout
```
**Rule:** every OTA is an audit-log entry.

## Pre-release checklist (Mobile Engineer + QA Engineer — native releases)

- [ ] `pnpm --filter mobile typecheck && test` pass · [ ] Detox golden path (launch → onboarding → primary surface render → core action)
- [ ] App icons verified · [ ] Screenshots updated if UI changed materially
- [ ] Privacy policy URL valid + reflects current data collection (**Security Reviewer VETO** if changed)
- [ ] Every `NSXxxUsageDescription` matches actual use · [ ] Tested on min OS (iOS 15+, Android 8+)
- [ ] Release notes prepared · [ ] EAS artifacts inspected (no debug symbols leaked)
- [ ] Compliance touch (anything `COMPLIANCE.md` declares — consent, channel rules) → Security Reviewer re-review even if only UI

## CI/CD (example)

```yaml
# .github/workflows/mobile-build.yml — on PR + main
jobs:
  build:
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
      - uses: actions/setup-node@v4 { node-version: '24', cache: 'pnpm' }
      - uses: expo/expo-github-action@v8 { eas-version: latest, token: ${{ secrets.EXPO_TOKEN }} }
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter mobile typecheck && pnpm --filter mobile test
      - if: github.event_name == 'pull_request'
        run: eas build --platform all --profile preview --non-interactive --no-wait
      - if: github.ref == 'refs/heads/main'
        run: eas build --platform all --profile production --non-interactive --no-wait
```
Submit + production rollout is a **manual** step gated on Stakeholder approval — no automated push to production.
```bash
eas submit --platform ios     --profile production --latest
eas submit --platform android --profile production --latest
```

## EAS Update (OTA) — the fast lane

```bash
git tag mobile-v1.4.3-ota
eas update --branch production --message "fix: null-safe delta render" --auto
eas update:view production --limit 5
```
**OTA rules:** JS/asset only (touched native → native build); test on preview channel first; audit-log row per prod OTA (what/why/when/rollback); watch error tracking 24h — auto-revert via `eas update --branch production --republish` if error rate > 2× baseline.

## Version management

```jsonc
// apps/mobile/app.json
{ "expo": { "version": "1.4.3", "ios": { "buildNumber": "45" }, "android": { "versionCode": 45 },
            "runtimeVersion": "1.4.0" } }   // OTA compatibility key — bump when native API changes
```
`runtimeVersion` is the OTA contract: a binary at `1.4.0` accepts any OTA built against `1.4.0`. Bump it when the JS bundle starts depending on new native code — otherwise OTAs silently fail to apply.

## Store review hazards

| Hazard | Context | Mitigation |
|---|---|---|
| Apple **5.1.1 Privacy** | any customer PII surface | nutrition label current; Security Reviewer reviews any data-collection change |
| Apple **4.0/4.5 Functionality** | app functional from day 1 | submit with the core flow working in TestFlight first |
| **Reviewer accounts** | Apple needs test creds | frozen review tenant with seed data |
| **Channel-disclosure** (e.g. automated calling) | required disclosure at the start of the interaction | documented in submission notes |

## Best practices / Never do

- EAS over raw native; manual production gate; OTA for JS-only; `runtimeVersion` discipline; error-tracking watch 24h (auto-revert OTA on spike); TestFlight + Play Internal first; `autoIncrement` (never hand-pick buildNumber/versionCode); audit-log every release + OTA.
- **Never:** push to production without TestFlight + Stakeholder approval; OTA a native-touching change (silent break); hand-bump versions (CI race); ship without 24h error-tracking watch; submit with a stale privacy-policy URL (Apple rejects; Security Reviewer VETO).

## Wiring

| Concern | Role |
|---|---|
| EAS Build config | **Mobile Engineer** + **Platform/SRE** |
| Native release flow / OTA dispatch | **Mobile Engineer** (+ **QA Engineer**) |
| Store submission + assets | **Mobile Engineer** + Stakeholder |
| Privacy nutrition label | **Security Reviewer** + Mobile Engineer |
| Post-release error-tracking watch | **Platform/SRE** + **Mobile Engineer** |

Related: [`mobile-surface`] (RN + Expo + OTA-vs-native policy), [`verification-before-completion`] (Stakeholder approval gate), [`observability`] (post-release watch), [`devops-aws`].

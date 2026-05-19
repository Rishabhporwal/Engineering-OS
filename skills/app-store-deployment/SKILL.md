---
name: app-store-deployment
description: Brain mobile release pipeline — EAS Build → TestFlight + Play Internal Track → manual approval → EAS Submit production. EAS Update for OTA JS-only changes; native version bumps go through the full store review. Use when shipping a mobile release, when configuring EAS profiles, when an OTA vs store-review decision is needed, when an App Store / Play Store review is rejected.
---

# App Store Deployment

Brain ships mobile via **EAS Build + EAS Submit + EAS Update** (Expo's managed pipeline). Native `xcodebuild` / `gradle` work is hidden behind EAS — Karan rarely touches the native side. Releases go: **dev → preview → TestFlight + Play Internal → manual founder approval → production rollout**. OTA updates (EAS Update) ship JS-only fixes within hours, bypassing store review.

## Why this matters for Brain

- **Brain is mobile-first** (see canon/BRAIN_TECHNICAL.md) — the Morning Brief depends on a working mobile binary
- **OTA is the fast path** — a JS-only fix can ship in 1 hour vs 1–7 days through store review
- **Native changes are the slow path** — anything that bumps the native build (new permission, new native module, SDK upgrade) requires App Store / Play Store review
- **EAS is the locked stack** — no raw `xcodebuild` or `gradle` workflows; the team standardizes on `eas` CLI

## EAS profiles (Brain canonical)

```jsonc
// apps/mobile/eas.json
{
  "cli": { "version": ">= 13.0.0" },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal",
      "channel": "development",
      "ios":     { "simulator": true },
      "env":     { "EXPO_PUBLIC_API_URL": "http://localhost:4000" }
    },
    "preview": {
      "distribution": "internal",
      "channel": "preview",
      "env":     { "EXPO_PUBLIC_API_URL": "https://staging.api.brain.pipadacapital.com" }
    },
    "production": {
      "channel": "production",
      "autoIncrement": "buildNumber",
      "env":     { "EXPO_PUBLIC_API_URL": "https://api.brain.pipadacapital.com" }
    }
  },
  "submit": {
    "production": {
      "ios":     { "appleId": "rishabhporwal95@gmail.com", "ascAppId": "...", "appleTeamId": "..." },
      "android": { "serviceAccountKeyPath": "./play-service-account.json", "track": "production" }
    }
  }
}
```

`channel` is the EAS Update channel — a build pulls OTAs only from its own channel. `production` binaries get production OTAs; `preview` binaries get preview OTAs.

## OTA vs store review — the decision tree

```
A change is needed in the mobile app.

  Is the change JS-only?
    (no native module added/removed, no permission added, no SDK upgrade,
     no Info.plist/AndroidManifest.xml change, no app.json native field change)
    │
    ├─ YES → ship via EAS Update (1–2 hours end-to-end)
    │        eas update --branch production --message "fix(brief): handle null delta"
    │
    └─ NO  → full native build + store review (1–7 days)
              eas build --platform all --profile production
              → TestFlight + Play Internal
              → Founder manual approval
              → eas submit --platform all --profile production
              → store review (Apple: 1–3d typical, Google: hours–1d)
              → production rollout
```

**Brain rule:** every OTA is a Decision Log entry. If we OTA-patch a Morning Brief bug at 09:00 IST after the morning's brief failed, the postmortem links back to the OTA decision.

## Pre-release checklist (Karan + Tanvi)

For native releases (NOT for OTAs — those have a lighter checklist):

- [ ] All tests passing: `pnpm --filter mobile typecheck && pnpm --filter mobile test`
- [ ] Detox e2e for golden paths: launch → onboarding → Morning Brief render → approve signal
- [ ] App icons in all sizes (handled by Expo automatically from `app.json` icon field, but verify)
- [ ] Screenshots updated if UI changed materially (App Store + Play listings)
- [ ] Privacy policy URL still valid + reflects current data collection (Shreya VETO if changed)
- [ ] Permissions justified — every entry in `app.json` `ios.infoPlist.NSXxxUsageDescription` matches actual use
- [ ] Tested on minimum supported OS (iOS 15+, Android 8+ per `app.json`)
- [ ] Release notes prepared (one-paragraph user-facing + linked PR list)
- [ ] EAS Build artifacts inspected (download IPA + APK from Expo dashboard; check no debug symbols leaked)
- [ ] India compliance touch (calling hours, NCPR, consent) → Shreya re-review even if only UI

## Brain CI/CD (canonical)

```yaml
# .github/workflows/mobile-build.yml — on PR + main
name: Mobile Build
on:
  pull_request: { paths: ['apps/mobile/**'] }
  push:         { branches: [main], paths: ['apps/mobile/**'] }
  workflow_dispatch:
    inputs:
      profile: { description: 'EAS profile', default: 'preview' }

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v3
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'pnpm' }
      - uses: expo/expo-github-action@v8
        with:
          eas-version: latest
          token: ${{ secrets.EXPO_TOKEN }}
      - run: pnpm install --frozen-lockfile
      - name: Verify
        run: |
          pnpm --filter mobile typecheck
          pnpm --filter mobile test
      - name: EAS Build (preview)
        if: github.event_name == 'pull_request'
        run: eas build --platform all --profile preview --non-interactive --no-wait
      - name: EAS Build (production, on main)
        if: github.ref == 'refs/heads/main'
        run: eas build --platform all --profile production --non-interactive --no-wait
```

Submit + production rollout is a **manual** step gated on Founder approval — no automated push to the App Store / Play Store for production.

```bash
# After Founder approves a build from TestFlight + Play Internal Track:
eas submit --platform ios     --profile production --latest
eas submit --platform android --profile production --latest
```

## EAS Update (OTA) — the fast lane

```bash
# Ship a JS-only fix to all production binaries within 1 hour
git tag mobile-v1.4.3-ota
eas update --branch production --message "fix(brief): null-safe delta render" --auto

# Monitor uptake in Expo dashboard
eas update:view production --limit 5
```

**OTA rules** (Brain):
- Only JS / asset changes — if you touched anything native, you must ship a native build
- Test on a preview-channel build FIRST (`eas update --branch preview`)
- Decision Log row for every prod OTA — what changed, why, when, rollback plan
- Watch error rate in Sentry for 24h after OTA — auto-revert via `eas update --branch production --republish` to the prior update if error rate jumps > 2x baseline

## Version management

```jsonc
// apps/mobile/app.json
{
  "expo": {
    "version": "1.4.3",                  // marketing version (semver)
    "ios":     { "buildNumber": "45" },  // auto-incremented by EAS (eas.json autoIncrement)
    "android": { "versionCode": 45 },    // auto-incremented by EAS
    "runtimeVersion": "1.4.0",           // OTA compatibility key — bump when native API changes
    ...
  }
}
```

`runtimeVersion` is the key contract for OTAs: a binary at `runtimeVersion: 1.4.0` will accept any OTA built against `1.4.0`. Bump the runtime version when the JS bundle starts depending on new native code — otherwise OTAs will silently fail to apply.

## Store review hazards (Brain context)

| Hazard | Brain context | Mitigation |
|---|---|---|
| Apple rejects on **5.1.1 Privacy** | Brain handles customer PII (Phase 3 inbox) | Privacy nutrition label kept current; Shreya reviews any data-collection change |
| Apple rejects on **4.0 Design / 4.5 Minimum Functionality** | Brain mobile is functional from day 1 (Morning Brief) | Submit with the Morning Brief working in TestFlight first |
| Google rejects on **Restricted content** | n/a for Brain (B2B SaaS) | — |
| **Reviewer accounts** | Apple needs test credentials | Maintain a frozen `apple-review@pipadacapital.com` workspace with seed data |
| **Calling-disclosure policy** (Phase 3 AI calling) | AI must disclose at call start (Brain hard-code) | Documented in submission notes |

## Best Practices

- **EAS over raw native builds** — managed pipeline, fewer pet workflows
- **Manual production gate** — Founder approves every production submission
- **OTA for JS-only fixes** — ship in hours
- **runtimeVersion discipline** — bump when native changes; otherwise OTAs silently fail
- **Sentry watch for 24h after every release** (native or OTA) — auto-revert OTA if error rate spikes
- **TestFlight + Play Internal first** — before production; Karan + Tanvi + Founder all install
- **Versioning autoIncrement** — never hand-pick a buildNumber/versionCode
- **Decision Log every release + OTA** — what changed, why, rollback plan

## Never Do

- Push directly to production without TestFlight + Founder approval
- Use OTA for a change that touches native code — `runtimeVersion` mismatch breaks the app silently
- Hand-bump buildNumber/versionCode — race conditions with parallel CI runs
- Ship to production without watching Sentry for 24h
- Submit with a privacy policy URL that doesn't reflect current data collection (Apple WILL reject; Shreya VETO)

## Brain wiring

| Concern | Owner | Reference |
|---|---|---|
| EAS Build configuration | **Karan** + **Jatin** | canon/BRAIN_TECHNICAL.md (build pipeline) |
| Native release flow | **Karan** | canon/BRAIN_TECHNICAL.md |
| OTA decision + dispatch | **Karan** + **Tanvi** | this skill |
| Store submission + assets | **Karan** + Founder | App Store Connect + Play Console |
| Privacy nutrition label | **Shreya** + Karan | canon/BRAIN_TECHNICAL.md (privacy) |
| Sentry post-release watch | **Jatin** + **Karan** | `observability` |
| Decision Log row per release | **Karan** | Decision Log |

Related Brain skills: `frontend-mobile` (broader RN + Expo playbook), `morning-brief-mobile` (the surface this releases), `verification-before-completion` (Founder approval gate), `observability` (post-release watch), `devops-aws` (the API side this app talks to).

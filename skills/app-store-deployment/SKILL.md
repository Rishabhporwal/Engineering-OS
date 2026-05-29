---
name: app-store-deployment
description: Brain mobile release pipeline — EAS Build → TestFlight/Play Internal → founder approval → EAS Submit; EAS Update for OTA JS-only; native bumps go to review.
---

# App Store Deployment

Brain ships mobile via **EAS Build + EAS Submit + EAS Update** (Expo's managed pipeline). Native `xcodebuild`/`gradle` is hidden behind EAS. Releases go: **dev → preview → TestFlight + Play Internal → manual founder approval → production rollout**. OTA (EAS Update) ships JS-only fixes in hours, bypassing store review.

## Why this matters for Brain

- Brain is mobile-first — the Morning Brief depends on a working binary.
- OTA is the fast path (JS-only fix in ~1h vs 1–7d store review); native changes (new permission/module, SDK upgrade) are the slow path.
- EAS is the locked stack — no raw `xcodebuild`/`gradle`; the team standardizes on `eas` CLI.

## EAS profiles (Brain canonical)

```jsonc
// apps/mobile/eas.json
{
  "cli": { "version": ">= 13.0.0" },
  "build": {
    "development": { "developmentClient": true, "distribution": "internal", "channel": "development",
                     "ios": { "simulator": true }, "env": { "EXPO_PUBLIC_API_URL": "http://localhost:4000" } },
    "preview":     { "distribution": "internal", "channel": "preview",
                     "env": { "EXPO_PUBLIC_API_URL": "https://staging.api.brain.pipadacapital.com" } },
    "production":  { "channel": "production", "autoIncrement": "buildNumber",
                     "env": { "EXPO_PUBLIC_API_URL": "https://api.brain.pipadacapital.com" } }
  },
  "submit": {
    "production": {
      "ios":     { "appleId": "rishabhporwal95@gmail.com", "ascAppId": "...", "appleTeamId": "..." },
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
   ├─ YES → EAS Update (1–2h):  eas update --branch production --message "fix(brief): handle null delta"
   └─ NO  → full native build + store review (1–7d):
            eas build --platform all --profile production → TestFlight + Play Internal
            → Founder manual approval → eas submit --platform all --profile production
            → review (Apple 1–3d, Google hours–1d) → production rollout
```
**Brain rule:** every OTA is a Decision Log entry.

## Pre-release checklist (Karan + Tanvi — native releases)

- [ ] `pnpm --filter mobile typecheck && test` pass · [ ] Detox golden path (launch → onboarding → brief render → approve signal)
- [ ] App icons verified · [ ] Screenshots updated if UI changed materially
- [ ] Privacy policy URL valid + reflects current data collection (**Shreya VETO** if changed)
- [ ] Every `NSXxxUsageDescription` matches actual use · [ ] Tested on min OS (iOS 15+, Android 8+)
- [ ] Release notes prepared · [ ] EAS artifacts inspected (no debug symbols leaked)
- [ ] India compliance touch (calling hours, NCPR, consent) → Shreya re-review even if only UI

## Brain CI/CD (canonical)

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
Submit + production rollout is a **manual** step gated on Founder approval — no automated push to production.
```bash
eas submit --platform ios     --profile production --latest
eas submit --platform android --profile production --latest
```

## EAS Update (OTA) — the fast lane

```bash
git tag mobile-v1.4.3-ota
eas update --branch production --message "fix(brief): null-safe delta render" --auto
eas update:view production --limit 5
```
**OTA rules:** JS/asset only (touched native → native build); test on preview channel first; Decision Log row per prod OTA (what/why/when/rollback); watch Sentry 24h — auto-revert via `eas update --branch production --republish` if error rate > 2× baseline.

## Version management

```jsonc
// apps/mobile/app.json
{ "expo": { "version": "1.4.3", "ios": { "buildNumber": "45" }, "android": { "versionCode": 45 },
            "runtimeVersion": "1.4.0" } }   // OTA compatibility key — bump when native API changes
```
`runtimeVersion` is the OTA contract: a binary at `1.4.0` accepts any OTA built against `1.4.0`. Bump it when the JS bundle starts depending on new native code — otherwise OTAs silently fail to apply.

## Store review hazards (Brain context)

| Hazard | Brain context | Mitigation |
|---|---|---|
| Apple **5.1.1 Privacy** | customer PII (Phase 3 inbox) | nutrition label current; Shreya reviews any data-collection change |
| Apple **4.0/4.5 Functionality** | functional from day 1 (brief) | submit with brief working in TestFlight first |
| **Reviewer accounts** | Apple needs test creds | frozen `apple-review@pipadacapital.com` workspace with seed data |
| **Calling-disclosure** (Phase 3 AI calling) | AI must disclose at call start | documented in submission notes |

## Best practices / Never do

- EAS over raw native; manual production gate; OTA for JS-only; `runtimeVersion` discipline; Sentry watch 24h (auto-revert OTA on spike); TestFlight + Play Internal first; `autoIncrement` (never hand-pick buildNumber/versionCode); Decision Log every release + OTA.
- **Never:** push to production without TestFlight + Founder approval; OTA a native-touching change (silent break); hand-bump versions (CI race); ship without 24h Sentry watch; submit with a stale privacy-policy URL (Apple rejects; Shreya VETO).

## Brain wiring

| Concern | Owner |
|---|---|
| EAS Build config | **Karan** + **Jatin** |
| Native release flow / OTA dispatch | **Karan** (+ **Tanvi**) |
| Store submission + assets | **Karan** + Founder |
| Privacy nutrition label | **Shreya** + Karan |
| Sentry post-release watch | **Jatin** + **Karan** |

Related: [`mobile-surface`] (RN + Expo + OTA-vs-native policy), [`morning-brief-mobile`] (the surface this releases), [`verification-before-completion`] (Founder approval gate), [`observability`] (post-release watch), [`devops-aws`].

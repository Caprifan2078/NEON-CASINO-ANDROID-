# NEON CASINO ROYALE — QA handoff, 2026-11-05

## Source of truth
- Current QA continuation: `qa/release-final-stress-20261104`. Do not modify `main` without explicit permission.
- The working v1.8.9 game lives inside `.ci/neon-s5-desktop-ios-sources.zip`, extracted as `s5platform/.../web/app.js`. Apply the verified `.ci/patch-p0-lease-cleanup.py` to **extracted copies**. The top-level `web/app.js` is older; do not replace the S5 code with it.
- GitHub repo is public. Never commit keystores, certificates with private keys, signing passwords, user saves, or credentials.

## Proven in automated CI
- [Long stress #41917026905](https://github.com/Caprifan2078/NEON-CASINO-ANDROID-/actions/runs/41917026905): 5,000 committed virtual-chip transactions, 4,400 UI navigation renders, check memory envelope and reload persistence. PASS. This does not equal hours of manual testing on hardware.
- [Math payout #41918450439](https://github.com/Caprifan2078/NEON-CASINO-ANDROID-/actions/runs/41918450439): 16,840 deterministic outcome comparisons before/after the wallet lease patch. PASS. Not all combinations of all 44 games are covered.
- [Browser gameplay #41825643556](https://github.com/Caprifan2078/NEON-CASINO-ANDROID-/actions/runs/41825643556): one playable start/bet action for 44/44 games. PASS. Not a proof that every final branch of all games settles correctly.
- [Wallet transition #41838166991](https://github.com/Caprifan2078/NEON-CASINO-ANDROID-/actions/runs/41838166991): active bets when switching modes, failed writes, once-only refunds and responsive layout. PASS.
- [**New** backup migration #42057592654](https://github.com/Caprifan2078/NEON-CASINO-ANDROID-/actions/runs/42057592654): old save versions v2/v3/v4 imported, v5 exported/imported/undone, two independent wallets and manual grants, five invalid files rejected without writes, simulated QuotaExceeded before checkpoint and during commit, recovery after browser restart and stale-lease release. PASS. Tested in an isolated browser profile, never against customer data.
- Historical Android emulation, iOS/iPad simulator, desktop/HTML jobs were successful on earlier v1.8.9 QA builds. A successful platform CI test is not a signed consumer release or physical-device proof.

## Open release gates
1. **Android**: owner-kept signing key + password must be installed in GitHub Actions Secrets before a genuinely owner-signed `assembleRelease`. The last observed owner-signing workflow #41819210066 failed closed due to missing secrets. A NEW release APK signed with a different key cannot update a previous APK with another certificate. Avoid deleting old installations before verified JSON export/import.
2. **iPhone/iPad**: physical-device IPA requires the owner's Apple Developer Team, private signing identity and provisioning profile. Simulator binary cannot be installed directly as a real-device app.
3. **macOS/Windows**: Developer ID/notarization (macOS) and trusted Authenticode (Windows) remain missing. QA/cross-compiled binaries are not equivalent to signed production distributions.
4. **Physical devices**: no verified end-to-end install/update/data-preservation suite on the owner's phone, iPad, and Windows/Linux/Mac computers.
5. **Coverage**: long-session load was accelerated. Continue full settlement paths and rare payout tests for 44 games, beyond mere successful action-start and representative mathematical distributions.

## Next safest concrete step
- Add real-finish QA coverage for multi-step game rounds (Blackjack splits/doubles, mines/tower, scratch, three-card/Caribbean/Teen Patti and delayed animations), preserving exact wallets and undo behavior.
- Then run full Android and desktop/HTML packaging regression on the same exact patched source snapshot, and create a versioned RC only after all gates pass.
- Sign only using owner-controlled secure credentials; avoid fallback to debug signer when producing a public release.

## Changes in this iteration
- Added `.ci/neon-backup-migration-matrix.py` and `.github/workflows/neon-backup-migration-matrix.yml`.
- Test #42057592654 PASS; no game logic or save schema changed, main untouched.
- Current status: **QA improved and verified**; public production release **not yet verified**.

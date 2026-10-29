# OffMenu shared source availability — fixed snapshot, 18 October 2026

Read-only source exports; not Git checkouts, current-task allocations or permission to activate data/runtime. Verify exact manifest/archive hashes before use. Preserve existing session, branch and dirty work. A fresh request must independently verify develop at scheduling time; these pins may become historical.

- develop: `/home/user/Documents/Codex/2026-10-18/offmenu-shared-source/develop-abecb99ee1125730ccbc2824b6ec49ffc5cc4302`
  Commit `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`; tree `cc06fde03b4f4b8d074e72aeb3e040a91e01dfc5`; 1014 files.
  Manifest `/home/user/Documents/Codex/2026-10-18/offmenu-worker00-shared-availability/develop-manifest.json` SHA256 `a900ba830ed48c8795aae30cb9ca808b8737ae897db35dd0f2d4a6daf3d61115`.
  Archive `/home/user/Documents/Codex/2026-10-18/offmenu-worker00-shared-availability/develop-abecb99ee1125730ccbc2824b6ec49ffc5cc4302.tar` SHA256 `c0c84baa2726b1df5625d0a57e021ca6d8bdf56697e1bc72c15fc2ac8bf10bcb`.

- handover-pending-unmerged: `/home/user/Documents/Codex/2026-10-18/offmenu-shared-source/handover-pending-unmerged-28a5ba731dbac090303f92ebb90013a204e9f509`
  Commit `28a5ba731dbac090303f92ebb90013a204e9f509`; tree `2edbee475f7d8f854cab5113c1d0bb56c60e029c`; 1028 files.
  Manifest `/home/user/Documents/Codex/2026-10-18/offmenu-worker00-shared-availability/handover-pending-unmerged-manifest.json` SHA256 `a44bcc34c973128aef31ba8adf49063d8a868cbf43461fa3477f09a768a829fa`.
  Archive `/home/user/Documents/Codex/2026-10-18/offmenu-worker00-shared-availability/handover-pending-unmerged-28a5ba731dbac090303f92ebb90013a204e9f509.tar` SHA256 `d6d9e61bb841c08e0239e1715147580289ef33987ed4a12c75c111fd7269abe5`.

The pending handover tree includes unmerged PR42 and pending UI requirements. It is NOT the accepted develop baseline. No shared Git alternates, refs, indexes or worktree files were changed. Existing isolated Git-object store remains `/tmp/offmenu-worker00-return-custody-20261018.git` for read-only inspection; `/tmp` is transient, while these home-directory exports and manifests are retained local artifacts. Reader/source custody receipt and proposal: `/home/user/Documents/Codex/2026-10-18/offmenu-worker00-shared-availability/`. Native worker use/acknowledgment remains separate from filesystem access.

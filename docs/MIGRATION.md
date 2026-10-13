# Codex migration

13 October 2026. Private destination: https://github.com/maldous/offmenu, branch main.

The original OffMenu_Codex_Handover.zip was restored. Application code and data files are unchanged; handover instructions have been updated to point to the existing private repository. All five attached PDFs match the bundled reports byte for byte. Four machine-readable research registers and their manifest are included. No production deployment or database change is part of this migration. Production state in CODEX_HANDOVER.md is historical and must be reconciled before implementation.

The saved Git history is preserved in migration/offmenu-checkpoint.bundle. To inspect it in a separate directory:

```bash
git clone migration/offmenu-checkpoint.bundle ../offmenu-history
```

Original verification output is retained in migration/original-resume-tests.log. See migration/migration-checks.log for checks run while restoring this package.

## Report SHA-256

```text
01-OffMenu_Basket_Normalization_Addendum.pdf: 0bfcec39c353542a9966a461486c65f424cf90bc72501dbabbd00681ad2fb864
02-OffMenu_Product_Review_and_Plan-1-.pdf: 2d1ec141bf3694f7dd1305b1dec9a78197bcf16ba156bfab7c4dfb2aebd44d9c
03-OffMenu_Enrichment_Discovery_249_Countries.pdf: 2db2a6fa89b62afc2976483ecf0fcb697bc2bf4bb97fdad3f9720a5a287d3567
04-OffMenu_User_Driven_Cache_and_Enrichment_Design-1-.pdf: 2e049a433c329421249a27ccbf92f15c64b9da2cc3adb065d8c6ddb13dff2ccd
05-OffMenu_Global_Shopping_Baskets.pdf: 5d4795811f472d0255e4c287a3401a2dbbcbd3991c8516c85dbe5341e9083a19
```

## Restoration checks

Fresh dependency install completed. 92 JavaScript tests and 7 Python tests pass; production build succeeds. Git bundle verified as complete, with saved main at dbdca1acb24bf4e92fd830c3905c08967c799101. These are local checks; live and device acceptance remains outstanding.

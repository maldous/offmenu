# Additional public-source acquisition — result, 22 October 2026

[Run 39724029085, attempt 1](https://github.com/maldous/offmenu/actions/runs/39724029085) is **completed / success**. The [verified completion receipt at `f9c75d1`](https://github.com/maldous/offmenu/blob/f9c75d1e38c4679ff660fa128bf1e52e0f3a81e3/.github/offmenu-runner/latest-receipt.json) reports passed readiness, source tests and acquisition steps. Terminal workflow success was checked separately because the receipt was published before the workflow became terminal.

## Acquired files, not normalized recipe/menu counts

| Source family | New files | Bytes |
|---|---:|---:|
| Foodista | 5 | 36,802,922 |
| ForkRecipe | 1 | 2,591,145 |
| Bègles | 2 | 62,360,152 |
| CNOUS | 26 | 5,710,371 |
| Toulouse | 4 | 512,705 |
| MedlinePlus | 12 | 340,707 |
| **Total: six families** | **50** | **108,318,002** |

The completed batch reported **zero blocked files and zero reused files**. Raw files remain on **Foo** under `outputs/additional-sources-20261022/source-cache`. No raw corpus was uploaded to GitHub. This acquisition did not mutate databases or perform normalization; file and byte totals do not establish complete, accepted or unique recipe/menu counts.

## Remaining scope

The [remaining-holds report](remaining-holds-triage/REPORT.md) reconciles **74 disabled source entries**, not 75 new corpora. Its [dispositions](remaining-holds-triage/all-disabled-dispositions.json) include 14 retained-family/no-verified-delta entries; these are entries, not an additional corpus or record count.

**No further corpus-scale batch is ready from this bounded triage.** The [three static-page candidates](remaining-holds-triage/static-page-candidate-fragment.json) remain unselected and disabled; they are not a dispatch request or whole-corpus coverage. Rights, access, terms and retained-overlap holds remain explicit.

This source/custody documentation update contains no datasets, credentials or execution changes and does not dispatch another job.

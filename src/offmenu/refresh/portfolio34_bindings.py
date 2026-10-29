"""Fixed Worker34 retained metadata declarations; no production admissions.

Only named JSON receipts/manifests may be opened. References inside them remain
declarations: this module never traverses to an original or parsed data body.
"""
from .portfolio34 import Binding, MetadataPin

ORIGINALS = '/home/user/src/offmenu-data/originals'
REPORTS = '/home/user/Documents/Codex/2026-10-13/task-3/reports'
LANE = REPORTS + '/country249-fixed64-priority/deliverables/owner-34'

BINDINGS = (
    Binding(
        'GQ', 'gq-beac-bes27-metadata', 'BEAC-BES-N27-retained',
        'regional-statistical-context-not-item-price-or-country-completeness',
        (MetadataPin('receipt.json', ORIGINALS + '/country-followthrough-20261015/owner-16/GQ/90dbd7aac961ee2cc020/receipt.json',
                     '05d753ce74854caea27fce0e7ace617f3dbf94213f36f2e2a3e66443fc0a06c1'),
         MetadataPin('return.json', LANE + '/GS/B02-W34/GQ16-return-consumed.json',
                     'ac4cea2517f633861d47abc5e964a43ae9ce1c3b5f53586164dea833932af97b')),
        (('releaseLabel', 'receipt.json', '/release'),
         ('originalSha256', 'receipt.json', '/sha256'),
         ('useStatement', 'receipt.json', '/licence'),
         ('remainingFields', 'return.json', '/remainingFields')),
        ('receipt.json', '/completed_utc'),
        ('acquisition-only-no-extraction-decision', 'denied-inege-imf-worldbank-no-retry'),
        ('table-page-row-column-selector', 'unit-index-vs-price', 'period-base-geography',
         'action-specific-use-and-attribution')),
    Binding(
        'GS', 'gs-bas-icefish-metadata', 'BAS-icefish-v1.0-1986-2023',
        'scientific-survey-context-not-human-food-composition',
        (MetadataPin('manifest.json', REPORTS + '/country-delivery-priority-20261017/owner-34/GS-BAS-v1-source-context/manifest.json',
                     '775a9b4e5afcc5f8b62c9baa3b779f22067c5212c444fdefd641932bb169f564'),),
        (('sourceTitle', 'manifest.json', '/sourceTitle'),
         ('edition', 'manifest.json', '/edition'),
         ('useEvidence', 'manifest.json', '/useEvidence'),
         ('catchMassDefinition', 'manifest.json', '/files/0/columns/14/sourceDefinition'),
         ('sourceFilePins', 'manifest.json', '/files/0/sourceAsset')),
        None,
        ('food-role-and-scope-unaccepted', 'unmatched13-reasons-unresolved'),
        ('original-acquisition-time-not-in-this-manifest', 'per-id-exclusion-semantics',
         'human-food-applicability-and-basis')),
    Binding(
        'GT', 'gt-ine-cba-metadata', 'CBAU-CBAR-2024-2026-update-2026-10-07',
        'official-expenditure-basket-not-personal-intake-prescription',
        (MetadataPin('receipt.json', ORIGINALS + '/country-followthrough-20261015/owner-20/GT/receipt.json',
                     '250997e0a46a1f62d3806a4b758d3834fa8ce9cff6560e8da8cd4711d68c241e'),
         MetadataPin('dictionary.json', LANE + '/GS/B02-W34/GT-metadata-resolution.json',
                     '234f2971b635ba09f425654a137661943b50e9e4bfe65b9d5c087a8c8f5cb864')),
        (('sourceContext', 'receipt.json', '/data_contexts/0'),
         ('useStatement', 'receipt.json', '/licence_evidence'),
         ('originalPins', 'receipt.json', '/verified_originals'),
         ('urbanOriginalAcquiredAt', 'receipt.json', '/responses/2/utc'),
         ('ruralOriginalAcquiredAt', 'receipt.json', '/responses/4/utc'),
         ('quantityDimensions', 'dictionary.json', '/resolved/quantityDimensions'),
         ('schemaDeclaration', 'dictionary.json', '/resolved/schema')),
        None,  # Per-workbook clocks retained; no shared bundle planner is installed.
        ('no-source-specific-transcription-decision',),
        ('reviewed-per-workbook-cache-binding', 'physical-sheet-range-selectors',
         'edible-vs-purchased', 'observation-denominators', 'currency-and-missing-rules')),
    Binding(
        'GU', 'gu-uog-cnep-metadata', 'retained-UOG-88-originals-2026-10-14',
        'publisher-recipe-card-inventory-not-parsed-recipe-corpus',
        (MetadataPin('manifest.json', ORIGINALS + '/country-followthrough-20261015/owner-21/GU/whole88-originals-manifest.json',
                     '343e745627d73a0bcbd32070d69524a054e101941dfcf47d7a709c6b25de5853'),),
        (('title', 'manifest.json', '/title'),
         ('extent', 'manifest.json', '/extent'),
         ('firstOriginalAcquiredAt', 'manifest.json', '/files/0/acquiredUTC'),
         ('rights', 'manifest.json', '/rights')),
        None,  # /files/*/acquiredUTC exists; no reviewed 88-input cache planner.
        ('derivative-not-granted', 'source-admission-withheld'),
        ('per-card-quantity-yield-selectors', 'card-specific-use-attribution',
         'per-original-acquisition-clock-binding')),
)

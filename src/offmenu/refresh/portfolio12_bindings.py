"""Worker12 reviewed metadata declarations, not production source admissions.

Absolute source paths are historical claims only. Nothing in this module opens
an original or creates rights. Missing types are reported by portfolio12.
"""
import json

BINDINGS = json.loads(r'''
[
  {
    "fixture": false,
    "holds": [
      "source-processing-not-selected",
      "retention-cache-scope-pending"
    ],
    "originalAcquiredAt": "2026-10-14T22:11:13.934002+00:00",
    "validatedAt": null,
    "cacheRights": "unknown",
    "types": [
      "prices/baskets"
    ],
    "units": [
      "source-currency/L",
      "source-currency/KG",
      "percent",
      "source-score-1-10",
      "LCU-index-January2018=1"
    ],
    "bases": [
      "modelled-monthly-market-series"
    ],
    "originPattern": "csv:row=(?:[2-9]|[1-9][0-9]+):column=(?:[1-9]|[1-5][0-9]|60)",
    "unknowns": [
      "bare-series-observed-versus-imputed",
      "non-oil-method-details",
      "dense-coverage-confidence-operational-definitions",
      "current-custody-not-appointed",
      "full-cache-action-use-decision"
    ],
    "key": "mm-rtfp-20261005",
    "country": "MM",
    "sourceId": "worldbank-mmr-rtfp",
    "releaseId": "MMR_RTFP_mkt_2007_2026-10-05",
    "evidence": [
      {
        "path": "/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-12/MM/main-member-validation.json",
        "sha256": "80666ef160842daae0fc3887d2c6df198ebeaae03572b317f6f16f8e416b6ede",
        "selectors": [
          "/sourceReceipt",
          "/archive",
          "/member",
          "/format",
          "/rightsBasis"
        ]
      },
      {
        "path": "/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-12/B01-W12/MM-semantic-bindings.json",
        "sha256": "4e8cfca27a0c537f005d783ae8f2f4cfd94e9f12d35f58dbd4827598a5485d20",
        "selectors": [
          ""
        ]
      }
    ],
    "assetClaims": [
      {
        "path": "/home/user/src/offmenu-data/originals/country-followthrough-20261015/owner-41/MM/1371c579dde879fdc9d4/MMR_RTFP_mkt_2007_2026-10-05.zip",
        "sha256": "ae22bc0449f77980751221ca65ca94622d1dea0faa14630c715ebeca7036912e",
        "bytes": 7470103
      },
      {
        "path": "MMR_RTFP_mkt_2007_2026-10-05.csv",
        "sha256": "503c7d825c95b0ec904cf8e8db9f10cda7af03d0b50c96a179a495f8098c1bd7",
        "bytes": 37313538
      }
    ],
    "selectorDeclaration": {
      "format": "csv-row-column-1based",
      "headers": [
        "ISO3",
        "country",
        "adm1_name",
        "adm2_name",
        "mkt_name",
        "lat",
        "lon",
        "geo_id",
        "price_date",
        "year",
        "month",
        "currency",
        "components",
        "start_dense_data",
        "last_survey_point",
        "data_coverage",
        "data_coverage_recent",
        "index_confidence_score",
        "spatially_interpolated",
        "oil",
        "onions",
        "pulses",
        "rice",
        "salt",
        "o_oil",
        "h_oil",
        "l_oil",
        "c_oil",
        "inflation_oil",
        "trust_oil",
        "o_onions",
        "h_onions",
        "l_onions",
        "c_onions",
        "inflation_onions",
        "trust_onions",
        "o_pulses",
        "h_pulses",
        "l_pulses",
        "c_pulses",
        "inflation_pulses",
        "trust_pulses",
        "o_rice",
        "h_rice",
        "l_rice",
        "c_rice",
        "inflation_rice",
        "trust_rice",
        "o_salt",
        "h_salt",
        "l_salt",
        "c_salt",
        "inflation_salt",
        "trust_salt",
        "o_food_price_index",
        "h_food_price_index",
        "l_food_price_index",
        "c_food_price_index",
        "inflation_food_price_index",
        "trust_food_price_index"
      ],
      "headerRow": 1,
      "dataRows": 71638,
      "coordinateRule": "values[i] is source column i+1 named headers[i]; row ordinal includes header. Physical lines explicit; rawRecord preserves all original lexical quoting."
    },
    "scope": "Full private literal candidate fidelity reviewed4278/Gateway4303; no numerical normalization, observation/merchant-offer claim or staging admission.",
    "nativeDenominators": {
      "oil": "L",
      "onions": "KG",
      "pulses": "KG",
      "rice": "KG",
      "salt": "KG"
    },
    "indexBasis": "LCU, Indexed, January 2018 = 1",
    "publisherMetadata": {
      "url": "https://microdata.worldbank.org/catalog/4501",
      "readDate": "2026-10-18",
      "selectors": [
        "Version",
        "Access policy",
        "Additional metadata / Ticker description"
      ],
      "scope": "Exact2026-10-05version; public metadata, not payload hash or new action-use decision."
    },
    "unitDeclarationStatus": "Native denominator labels and index base source-bound; source currency stays literal, composite currency/unit rendering still requires scoped semantic review."
  },
  {
    "fixture": false,
    "holds": [
      "source-processing-not-selected",
      "retention-cache-scope-pending"
    ],
    "originalAcquiredAt": null,
    "validatedAt": null,
    "cacheRights": "unknown",
    "types": [
      "prices/baskets"
    ],
    "units": [
      "MOP/kg",
      "MOP/each"
    ],
    "bases": [
      "historical-consumer-price-survey-average"
    ],
    "originPattern": "pdf:page=(25|26):block=[1-3]:row=([1-9]|1[0-6]):column=([1-9]|1[0-9]|2[0-2])",
    "unknowns": [
      "original-acquisition-time-not-bound-here",
      "cache30day-retention-review",
      "current-original-custody"
    ],
    "key": "mo-dsec-2025m01-t37",
    "country": "MO",
    "sourceId": "dsec-retail-price-survey",
    "releaseId": "E_BME_PUB_2025_M01-table3.7",
    "evidence": [
      {
        "path": "/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-12/MO/author-receipt.json",
        "sha256": "293a035e4e73b2d9916ba62803ae08de5b28ea4b931145d20ef796a5e5c2bcb4",
        "selectors": [
          "/candidateArtifacts",
          "/counts"
        ]
      },
      {
        "path": "/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-12/review05-result-binding.json",
        "sha256": "f038f9a72f8abb47104831039fc49788272bad19ab88215a9663b61770fedf25",
        "selectors": [
          ""
        ]
      },
      {
        "path": "/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-12/MO/retail-price-validation.json",
        "sha256": "530747209a9f8fa0d3d5e9d0f533bff5bcd6b9589538771e5e35749f464d9d29",
        "selectors": [
          "/rowGroups"
        ]
      }
    ],
    "assetClaims": [
      {
        "path": "/home/user/src/offmenu-data/originals/country-followthrough-20261015/owner-43/MO/E_BME_PUB_2025_M01.aspx",
        "sha256": "7489e95a6a98d0dcd3ff52568d3ca462e27811a77c93edb46935e2992aeef548",
        "bytes": null
      }
    ],
    "selectorDeclaration": {
      "format": "pdf-bbox-table",
      "physicalPages": [
        25,
        26
      ],
      "table": "3.7",
      "itemColumns": 22,
      "valueCount": 352,
      "periods": "annual2022/2023/2024;monthlyDec2023,Jan-Dec2024",
      "unitExceptionsEach": [
        "Hen egg",
        "Orange",
        "Apple"
      ]
    },
    "scope": "352 source price strings reviewed4278/Gateway4303; reproduction requires DSEC attribution; no present-day merchant offers."
  },
  {
    "fixture": false,
    "holds": [
      "source-processing-not-selected",
      "retention-cache-scope-pending",
      "mali2004-print-only-no-authorized-digital-original",
      "recipe-yearbook-source-evaluation-only",
      "meteo-denial-no-retry"
    ],
    "originalAcquiredAt": null,
    "validatedAt": null,
    "cacheRights": "unknown",
    "types": [
      "recipes",
      "nutrition",
      "prices/baskets"
    ],
    "units": [],
    "bases": [],
    "originPattern": null,
    "unknowns": [
      "structured-record-selectors",
      "derivation-use",
      "composition-digital-manifest"
    ],
    "key": "ml-retained-document-evidence",
    "country": "ML",
    "sourceId": "mali-source-evaluation",
    "releaseId": "recipe2020-yearbook2023-and-composition2004-held",
    "evidence": [
      {
        "path": "/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-12/ML/retained-document-integrity.json",
        "sha256": "c74c3c5ca416f870da7e6e003a65c7e2233b764320c1b48ab56ad299d099d85e",
        "selectors": [
          "/checks",
          "/parsedRecipeRecords"
        ]
      },
      {
        "path": "/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-12/B01-W12/ML-returned-evidence-binding.json",
        "sha256": "739caedffc4ecb8c184f21977856fc38e429f4b4e7f66324da506288bf7e6dd1",
        "selectors": [
          "/resolved",
          "/remaining"
        ]
      }
    ],
    "assetClaims": [
      {
        "path": "/home/user/src/offmenu-data/originals/country-followthrough-20261015/owner-40/ML/61afb34c42bb38a46c410846/original.pdf",
        "sha256": "5c35b25e7030e8e2681dbac59cc2791dac5b4e3edf106b5d51d42768f740463f",
        "bytes": 2961390
      },
      {
        "path": "/home/user/src/offmenu-data/originals/country-followthrough-20261015/owner-40/ML/9d11b3a780c4a45a9e27d0f9/original.pdf",
        "sha256": "fe81aa6ee4316aaebd9d62dfb19536de4612aed45c6987b3f47d6cd414a29ac8",
        "bytes": 4210748
      }
    ],
    "selectorDeclaration": null,
    "scope": "Document integrity22+81pages only,0new recipe/nutrient records; no source-use expansion."
  },
  {
    "fixture": false,
    "holds": [
      "source-processing-not-selected",
      "retention-cache-scope-pending",
      "source-specific-no-body-rights-access-hold"
    ],
    "originalAcquiredAt": null,
    "validatedAt": null,
    "cacheRights": "unknown",
    "types": [
      "nutrition",
      "prices/baskets"
    ],
    "units": [],
    "bases": [],
    "originPattern": null,
    "unknowns": [
      "verified-title-edition-language",
      "finite-original-manifest",
      "action-use",
      "source-custody",
      "structured-record-selectors"
    ],
    "key": "mn-nso2016-metadata",
    "country": "MN",
    "sourceId": "mn-nso-foodsecurity",
    "releaseId": "2016-receipt-claim-unverified",
    "evidence": [
      {
        "path": "/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-12/B01-W12/MN-release-use-binding.json",
        "sha256": "2b41542bbf1e78acc44752d9977078cb102836f4bd7aa82eddac8e334560f5be",
        "selectors": [
          ""
        ]
      },
      {
        "path": "/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-12/MN/author-receipt.json",
        "sha256": "f3d6b4752ff7f4e29aed08e3665c6aa080f52e78ab2e975a4d4550a54139855a",
        "selectors": [
          ""
        ]
      }
    ],
    "assetClaims": [],
    "selectorDeclaration": null,
    "scope": "Receipt metadata only;0source body/parsed data records; restricted routes not retried."
  }
]
''')

"""Inert Worker10 code catalogue; exact JSON mirror, no source I/O or admission."""

from copy import deepcopy

CATALOGUE = {'schemaVersion': 'offmenu-worker10-bindings/1',
 'owner': 10,
 'baselineCommit': 'abecb99ee1125730ccbc2824b6ec49ffc5cc4302',
 'countries': ['KW', 'NO', 'SA', 'UA'],
 'requiredTypes': ['ingredients',
                   'recipes',
                   'nutrition',
                   'retailers/providers',
                   'prices/baskets',
                   'dietary references'],
 'scope': 'retained metadata to staging only; no source payload normalization or acceptance',
 'rightsPolicy': 'Unknown grant is not legal prohibition. Public visibility is not permission. '
                 'Evidence roles never confer acceptance.',
 'bindings': [{'id': 'kw-pista-menu',
               'country': 'KW',
               'sourceId': 'kw-pista-menu',
               'releaseId': 'retained-metadata-159fc1f04602d90c',
               'releaseIdentityScope': 'Receipt snapshot identity; publisher edition is only the '
                                       'explicitly selected release field, never the validation '
                                       'date.',
               'metadataPath': '/home/user/src/offmenu-data/originals/country-followthrough-20261015/owner-62/KW/93d29f9d493c658e9d21/receipt.json',
               'inputPath': 'metadata/kw-pista-menu.json',
               'sha256': '159fc1f04602d90cb90b0fc791a02b4353097fe943c72be503cb13eb2325b191',
               'bytes': 2113,
               'types': ['retailers/providers', 'prices/baskets'],
               'sourceStage': 'held',
               'evidenceRole': 'Complete single-venue original recorded; no parsed menu or '
                               'national coverage.',
               'fields': {'sourceUrl': '/canonicalURL',
                          'releaseStatement': '/release',
                          'rightsStatement': '/redistributionRights',
                          'acquisitionStatement': '/acquisitionRights',
                          'extentStatement': '/sourceExtent',
                          'recordedBodyBytes': '/responses/0/bytes',
                          'recordedBodySha256': '/responses/0/sha256',
                          'recordedCompleteResponse': '/responses/0/completeResponse'},
               'originalAcquiredAtSelector': '/responses/0/utc',
               'nativeUnitsAndBasis': {'currency': None,
                                       'portion': None,
                                       'units': None,
                                       'bodySelectors': None},
               'sourcePayloadAdapter': 'not-authorized; metadata projection uses shared core and '
                                       'field_provenance only',
               'prerequisites': [{'code': 'use-and-custody-unqualified',
                                  'kind': 'authorization',
                                  'owner': 'source62/Gateway',
                                  'nextAction': 'Provide exact local derivative '
                                                'use/custody/attribution qualification; source62 '
                                                'current metadata retention does not transfer raw '
                                                'writer.'},
                                 {'code': 'currency-portion-not-held',
                                  'kind': 'missing-input',
                                  'owner': 'source62',
                                  'nextAction': 'Exact source-native currency and portion/unit '
                                                'evidence is not held; do not infer from country '
                                                'or venue.'},
                                 {'code': 'cookbook-timedout-no-retry',
                                  'kind': 'technical-failure',
                                  'owner': 'Gateway/source62',
                                  'nextAction': 'Retain separate zero-byte MOH cookbook failure; '
                                                'no retry or recipe inference.'}]},
              {'id': 'no-smilefjes',
               'country': 'NO',
               'sourceId': 'no-smilefjes',
               'releaseId': 'retained-metadata-18d5c4afd2ff565d',
               'releaseIdentityScope': 'Receipt snapshot identity; publisher edition is only the '
                                       'explicitly selected release field, never the validation '
                                       'date.',
               'metadataPath': '/home/user/src/offmenu-data/originals/country-followthrough-20261015/owner-10/NO/45e332e7b83ad2bfe6cc/receipt.json',
               'inputPath': 'metadata/no-smilefjes.json',
               'sha256': '18d5c4afd2ff565d1cc0b21b800ca4ac397fad258a2f0fac495c46b6447d902b',
               'bytes': 1843,
               'types': ['retailers/providers'],
               'sourceStage': 'held',
               'evidenceRole': 'Recorded complete original pending extent inspection; inspection '
                               'registry is not a complete business directory.',
               'fields': {'sourceUrl': '/canonicalURL',
                          'releaseStatement': '/release',
                          'rightsStatement': '/licence',
                          'extentStatement': '/extent',
                          'recordedStatus': '/status',
                          'recordedBodyBytes': '/requests/0/bytes',
                          'recordedBodySha256': '/requests/0/sha256'},
               'originalAcquiredAtSelector': '/requests/0/utc',
               'nativeUnitsAndBasis': {'inspectionScale': None,
                                       'bodySelectors': None,
                                       'csvDialect': None},
               'sourcePayloadAdapter': 'not-authorized; metadata projection uses shared core and '
                                       'field_provenance only',
               'prerequisites': [{'code': 'version-use-privacy-attribution-open',
                                  'kind': 'authorization',
                                  'owner': 'Gateway/source10',
                                  'nextAction': 'Reuse exact prior qualification; no CC-BY '
                                                'statement-to-app-use permission inference.'},
                                 {'code': 'extent-and-dialect-unqualified',
                                  'kind': 'missing-input',
                                  'owner': 'source10/Gateway',
                                  'nextAction': 'Supply separately authorized existing '
                                                'extent/header metadata before source parsing; no '
                                                'body read selected.'}]},
              {'id': 'no-composition',
               'country': 'NO',
               'sourceId': 'no-composition',
               'releaseId': 'retained-metadata-b17ed911288c6dc6',
               'releaseIdentityScope': 'Receipt snapshot identity; publisher edition is only the '
                                       'explicitly selected release field, never the validation '
                                       'date.',
               'metadataPath': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-10/NO/composition-metadata-validation.json',
               'inputPath': 'metadata/no-composition.json',
               'sha256': 'b17ed911288c6dc6d066396dd630b33de5755839fe6e2c37d8da3a57f486d8d5',
               'bytes': 4334,
               'types': ['ingredients', 'nutrition'],
               'sourceStage': 'held',
               'evidenceRole': 'Prior metadata validation reused: 1 metadata row, 0 food samples. '
                               'Manifest count2121 is recorded only.',
               'fields': {'releaseStatement': '/sourceSemantics/version/publisherRelease',
                          'apiVersion': '/sourceSemantics/version/apiVersion',
                          'basisValue': '/sourceSemantics/basis/value',
                          'basisUnit': '/sourceSemantics/basis/unit',
                          'basisDefinition': '/sourceSemantics/basis/definition',
                          'recordedManifestSha256': '/normalizedManifest/sha256',
                          'recordedRows': '/normalizedManifest/recordedRows',
                          'bodyRowsRecounted': '/normalizedManifest/bodyRowsRecounted',
                          'rightsStatement': '/licenceConflict/laterSourceSpecificReceipt/redistribution',
                          'recordedManifestPath': '/normalizedManifest/path',
                          'recordedManifestBytes': '/normalizedManifest/bytes',
                          'recordedMetadataGitCommit': '/gitCommit'},
               'originalAcquiredAtSelector': None,
               'nativeUnitsAndBasis': {'value': 100,
                                       'unit': 'g',
                                       'definition': 'edible food',
                                       'nutrientUnits': 'nutrient-specific; no sum/by-difference '
                                                        'equivalence',
                                       'nulls': 'not zero',
                                       'bodySelectors': None},
               'sourcePayloadAdapter': 'not-authorized; metadata projection uses shared core and '
                                       'field_provenance only',
               'prerequisites': [{'code': 'derivative-rights-unqualified',
                                  'kind': 'authorization',
                                  'owner': 'Gateway/source04',
                                  'nextAction': 'Retain later source-specific UNKNOWN/UNQUALIFIED '
                                                'grant; API caching text does not establish '
                                                'derivative/admission rights.'},
                                 {'code': 'native-no-crash-hold',
                                  'kind': 'technical-hold',
                                  'owner': 'Gateway/native custodian',
                                  'nextAction': 'No native NO/FR engine runs; this binding uses '
                                                'metadata only.'},
                                 {'code': 'original-age-and-schema-unknown',
                                  'kind': 'missing-input',
                                  'owner': 'source04',
                                  'nextAction': 'Provide exact original acquisition timestamp and '
                                                'permitted native field selectors; validation '
                                                'timestamp is not acquisition timestamp.'}]},
              {'id': 'sa-cpi-method',
               'country': 'SA',
               'sourceId': 'sa-cpi-method',
               'releaseId': 'retained-metadata-05151223106dfcf9',
               'releaseIdentityScope': 'Receipt snapshot identity; publisher edition is only the '
                                       'explicitly selected release field, never the validation '
                                       'date.',
               'metadataPath': '/home/user/src/offmenu-data/originals/country-acquisition-20261015/source-queue/owner-47/c2113eabe10c3db3496d/receipt.json',
               'inputPath': 'metadata/sa-cpi-method.json',
               'sha256': '05151223106dfcf90c9c6b4323530a45ecdf7040687fd7260f8a1f78cc80fc54',
               'bytes': 4716,
               'types': ['prices/baskets'],
               'sourceStage': 'metadata-only',
               'evidenceRole': 'Methodology and policy documents only; no numeric monthly release '
                               'or item prices.',
               'fields': {'sourceUrl': '/source/url',
                          'releaseStatement': '/release_scope/version',
                          'extentStatement': '/release_scope/source_extent',
                          'rightsStatement': '/acquisition_rights',
                          'redistributionStatement': '/redistribution_rights',
                          'recordedMethodBytes': '/new_requests/0/response_body_bytes',
                          'recordedMethodSha256': '/new_requests/0/sha256',
                          'recordedPolicySha256': '/new_requests/1/sha256',
                          'wholeDatasetAcquired': '/whole_dataset_acquired'},
               'originalAcquiredAtSelector': '/new_requests/0/requested_utc',
               'nativeUnitsAndBasis': {'indexBase': None,
                                       'itemPriceCurrency': None,
                                       'basketQuantities': None,
                                       'bodySelectors': None,
                                       'method': 'CPI indicators cannot substitute for price '
                                                 'levels or basket quantities.'},
               'sourcePayloadAdapter': 'not-authorized; metadata projection uses shared core and '
                                       'field_provenance only',
               'prerequisites': [{'code': 'numeric-release-and-custodian-missing',
                                  'kind': 'missing-input',
                                  'owner': 'Morgan/Gateway; source47/26 metadata holders',
                                  'nextAction': 'Resolve existing correlated request '
                                                'B01-W10-KW62-SA47-26-retained-metadata-v1, no '
                                                'duplicate request/acquisition. Provide exact '
                                                'monthly numeric release, '
                                                'table/columns/period/geography/units/status.'},
                                 {'code': 'numeric-scope-not-inherited',
                                  'kind': 'authorization',
                                  'owner': 'Gateway/source custodian',
                                  'nextAction': 'Policy1.2.2 qualified retained method/policy '
                                                'metadata only; numeric release '
                                                'attribution/changes/third-party exclusions '
                                                'require exact binding.'}]},
              {'id': 'ua-edozvil',
               'country': 'UA',
               'sourceId': 'ua-edozvil',
               'releaseId': 'retained-metadata-d4c2a3f79d551aef',
               'releaseIdentityScope': 'Receipt snapshot identity; publisher edition is only the '
                                       'explicitly selected release field, never the validation '
                                       'date.',
               'metadataPath': '/home/user/src/offmenu-data/originals/country-acquisition-20261015/source-queue/owner-10/7ecce3bc98dab7f9ab9d/receipt.json',
               'inputPath': 'metadata/ua-edozvil.json',
               'sha256': 'd4c2a3f79d551aef701157d223205a4e91430af21ab2d6877185ca6246df7d63',
               'bytes': 20467,
               'types': ['retailers/providers'],
               'sourceStage': 'held',
               'evidenceRole': 'Finite licence snapshot; prior restricted structural '
                               'validation4044 records, not food providers.',
               'fields': {'releaseStatement': '/release',
                          'rightsStatement': '/licence/redistribution',
                          'recordedStatus': '/status',
                          'recordedRecords': '/extent/records',
                          'recordedUniqueIds': '/extent/sourceIdsUnique',
                          'sourceUrl': '/newRequests/9/url',
                          'recordedBodyBytes': '/newRequests/9/bodyBytes',
                          'recordedBodySha256': '/newRequests/9/sha256'},
               'originalAcquiredAtSelector': '/newRequests/9/utc',
               'nativeUnitsAndBasis': {'bodySelectors': '/*/id observed historically; NOT enabled',
                                       'foodSubset': None,
                                       'dateStatusMeaning': None,
                                       'naturalPersonPrivacy': 'unqualified'},
               'sourcePayloadAdapter': 'not-authorized; metadata projection uses shared core and '
                                       'field_provenance only',
               'prerequisites': [{'code': 'restricted-inspection-only',
                                  'kind': 'authorization',
                                  'owner': 'Gateway/source10',
                                  'nextAction': 'No derivative/app/privacy/provider admission or '
                                                'PII projection; source inspection grant is '
                                                'narrower.'},
                                 {'code': 'food-subset-and-semantics-missing',
                                  'kind': 'missing-input',
                                  'owner': 'source10/source publisher evidence',
                                  'nextAction': 'Prior metadata shows typesOfEconomicActivities '
                                                'null4044/4044; cannot derive food subset. Need '
                                                'status/date/geography definitions and permitted '
                                                'source selectors.'},
                                 {'code': 'regional-cpi-separate',
                                  'kind': 'missing-input',
                                  'owner': 'source43/method32/Gateway',
                                  'nextAction': 'Retained Kharkiv CPI is regional index evidence, '
                                                'not national item prices/basket quantities. No '
                                                'held source retry.'}]}],
 'reusedQualifications': [{'path': '/home/user/src/offmenu-data/user-selected-receipt-metadata-20261016/owner-10/NO/qualification-18d5c4af.json',
                           'sha256': '5281218b5269b2c036bc7431d005eb661df29302b84df59c2c687660b654bda7',
                           'resultEventSequence': 1340},
                          {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-10/B01-W10/returned-KW62-20261017/returned-evidence-binding.json',
                           'sha256': 'f1c771b7f5fe2f74eae447286449deb22a6eac0c7c9bda74ab9dcd209204a6b8',
                           'resultEventSequence': 5121},
                          {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-10/UA/restricted-shape-validation-20261017-01a146f5.json',
                           'sha256': '35c8cb11b3289d481f7bc183ecb546686491ba750e945ef6d01cb8266f50c5b3',
                           'resultEventSequence': 4522},
                          {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-10/B01-W10/resolution-result.json',
                           'sha256': '2039ce2323599d313fc227a6c8bf182534e57da6648cf9b56ef9553fcd38b322',
                           'resultEventSequence': 4803}]}

def catalogue():
    """Return an independent declaration copy for each caller."""
    return deepcopy(CATALOGUE)

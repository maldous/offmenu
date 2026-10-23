"""Inert Worker16 code catalogue; JSON mirror retained for audit, no I/O."""

CATALOGUE = {'schema': 'offmenu-portfolio16-metadata-bindings/1',
 'metadataOnly': True,
 'trustedProfile': 'Repository-reviewed portfolio configuration; not runtime-supplied source '
                   'permission.',
 'baseCommit': 'abecb99ee1125730ccbc2824b6ec49ffc5cc4302',
 'bindings': [{'source_id': 'portfolio16-bn-moh-download-chain',
               'country': 'BN',
               'release_id': 'MOH-linked-2020-file1yiirvjZ7bOW5FzltFOBoERSIPFlRBTrG',
               'metadata_path': 'BN/deliverable-validation.json',
               'metadata_sha256': 'a9bc92ed1795bfbcec0e50dc4c92d73dafe3b6fa425bf03360a0c29d38f660db',
               'metadata_bytes': 4719,
               'original_acquired_at': '2026-10-15T22:22:02.289960+00:00',
               'last_validated_pointer': '/recordedUTC',
               'selectors': {'reportCountry': '/country',
                             'observationsInCountryReport': '/measured/observationRows',
                             'structuralFailuresInCountryReport': '/measured/failedChecks'},
               'declarations': {'countryApplicability': 'BN',
                                'dataType': 'acquisition-control',
                                'nativeUnitDeclaration': None,
                                'nativeBasisDeclaration': None,
                                'taxTreatment': None,
                                'serviceTreatment': None,
                                'sourceDatasetAccepted': False},
               'holds': ['private-inspection-only', 'no-source-processing-selected'],
               'evidence': {'retainedStagedAsset': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/BN/download-chain.json',
                                                    'bytes': 630,
                                                    'sha256': 'a8b36b02bf05cbdfd2e8965953afbcfd4b080f614aa0963ce10caa6c58903d7e'},
                            'retainedManifest': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/manifest.json',
                                                 'bytes': 25064,
                                                 'sha256': 'ce3a3ce71137d04d10e69dffeba04f39c72c1caff02006f71d4fa0c72d6af357'},
                            'countryResultManifest': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/batch-result.json',
                                                      'bytes': 5056,
                                                      'sha256': '899a05000ad486a1c71ed50bdbc62dd59c88fd7ad2bf2f89b6eb172fb479d609'},
                            'metadataValidation': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/BN/deliverable-validation.json',
                                                   'bytes': 4719,
                                                   'sha256': 'a9bc92ed1795bfbcec0e50dc4c92d73dafe3b6fa425bf03360a0c29d38f660db'},
                            'originalAcquisitionReceipt': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/BN/originals/ec8f0c500e9e48528033/receipt.json',
                                                           'bytes': 1378,
                                                           'sha256': '060cde402f52b679832af6a5697225da40b018589d052b1b36cd089e2ca518cd'},
                            'originalAcquisitionSelector': '/utc',
                            'stagingSnapshotIsNotNewOriginalAcquisition': True,
                            'nativeDeclarationEvidence': 'Prior scoped structural/currency checks '
                                                         'bound in metadataValidation; '
                                                         'declarations are reviewed code '
                                                         'annotations, not newly read source '
                                                         'cells.',
                            'recordedSourceCoordinateDeclarations': {},
                            'sourceCoordinateStatus': 'EXISTING_STAGED_SELECTOR_DECLARATIONS_NOT_REPLAYED_OR_ACCEPTED',
                            'sourceCoordinateExtent': 'Examples for retained first record only, '
                                                      'not all-record field-origin qualification. '
                                                      'Missing coordinates are explicit null.',
                            'rightsAndScopeAcceptance': 'Holds retained. No SourceContract, source '
                                                        'use, real dataset STAGING acceptance or '
                                                        'country completion installed.',
                            'acquiredAtStatus': 'source-receipt-utc-as-recorded',
                            'countryTypeApplicability': {'ingredients': {'state': 'missing-ingredient-source',
                                                                         'accepted': False,
                                                                         'scopeEvidence': 'Existing '
                                                                                          'country '
                                                                                          'category-coverage-and-gaps.json '
                                                                                          'at3829; '
                                                                                          'no new '
                                                                                          'category '
                                                                                          'validation '
                                                                                          'or '
                                                                                          'completion.'},
                                                         'recipes': {'state': 'missing-recipe-source',
                                                                     'accepted': False,
                                                                     'scopeEvidence': 'Existing '
                                                                                      'country '
                                                                                      'category-coverage-and-gaps.json '
                                                                                      'at3829; no '
                                                                                      'new '
                                                                                      'category '
                                                                                      'validation '
                                                                                      'or '
                                                                                      'completion.'},
                                                         'nutrition': {'state': 'reference-not-analytical-composition',
                                                                       'accepted': False,
                                                                       'scopeEvidence': 'Existing '
                                                                                        'country '
                                                                                        'category-coverage-and-gaps.json '
                                                                                        'at3829; '
                                                                                        'no new '
                                                                                        'category '
                                                                                        'validation '
                                                                                        'or '
                                                                                        'completion.'},
                                                         'retailers/providers': {'state': 'missing-provider-source',
                                                                                 'accepted': False,
                                                                                 'scopeEvidence': 'Existing '
                                                                                                  'country '
                                                                                                  'category-coverage-and-gaps.json '
                                                                                                  'at3829; '
                                                                                                  'no '
                                                                                                  'new '
                                                                                                  'category '
                                                                                                  'validation '
                                                                                                  'or '
                                                                                                  'completion.'},
                                                         'prices/baskets': {'state': 'missing-price-source',
                                                                            'accepted': False,
                                                                            'scopeEvidence': 'Existing '
                                                                                             'country '
                                                                                             'category-coverage-and-gaps.json '
                                                                                             'at3829; '
                                                                                             'no '
                                                                                             'new '
                                                                                             'category '
                                                                                             'validation '
                                                                                             'or '
                                                                                             'completion.'},
                                                         'dietary references': {'state': 'held-commercial-bibliographic-scope',
                                                                                'accepted': False,
                                                                                'scopeEvidence': 'Existing '
                                                                                                 'country '
                                                                                                 'category-coverage-and-gaps.json '
                                                                                                 'at3829; '
                                                                                                 'no '
                                                                                                 'new '
                                                                                                 'category '
                                                                                                 'validation '
                                                                                                 'or '
                                                                                                 'completion.'}}},
               'expected_values': {'reportCountry': 'BN', 'structuralFailuresInCountryReport': 0}},
              {'source_id': 'portfolio16-bn-moh-guideline',
               'country': 'BN',
               'release_id': 'MOH-NDG-2020-ISBN978-99917-50-13-2',
               'metadata_path': 'BN/deliverable-validation.json',
               'metadata_sha256': 'a9bc92ed1795bfbcec0e50dc4c92d73dafe3b6fa425bf03360a0c29d38f660db',
               'metadata_bytes': 4719,
               'original_acquired_at': '2026-10-15T22:22:02.289960+00:00',
               'last_validated_pointer': '/recordedUTC',
               'selectors': {'reportCountry': '/country',
                             'observationsInCountryReport': '/measured/observationRows',
                             'structuralFailuresInCountryReport': '/measured/failedChecks'},
               'declarations': {'countryApplicability': 'BN',
                                'dataType': 'dietary-reference',
                                'nativeUnitDeclaration': None,
                                'nativeBasisDeclaration': None,
                                'taxTreatment': None,
                                'serviceTreatment': None,
                                'sourceDatasetAccepted': False},
               'holds': ['commercial-bibliographic-applicability-unestablished',
                         'no-target-adoption'],
               'evidence': {'retainedStagedAsset': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/BN/nutrition-dietary-reference.json',
                                                    'bytes': 1583,
                                                    'sha256': '3efa8a8b45e378a2b16e7d1a416f078c38473eac0494d891cb546cc451bef4c0'},
                            'retainedManifest': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/manifest.json',
                                                 'bytes': 25064,
                                                 'sha256': 'ce3a3ce71137d04d10e69dffeba04f39c72c1caff02006f71d4fa0c72d6af357'},
                            'countryResultManifest': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/batch-result.json',
                                                      'bytes': 5056,
                                                      'sha256': '899a05000ad486a1c71ed50bdbc62dd59c88fd7ad2bf2f89b6eb172fb479d609'},
                            'metadataValidation': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/BN/deliverable-validation.json',
                                                   'bytes': 4719,
                                                   'sha256': 'a9bc92ed1795bfbcec0e50dc4c92d73dafe3b6fa425bf03360a0c29d38f660db'},
                            'originalAcquisitionReceipt': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/BN/originals/ec8f0c500e9e48528033/receipt.json',
                                                           'bytes': 1378,
                                                           'sha256': '060cde402f52b679832af6a5697225da40b018589d052b1b36cd089e2ca518cd'},
                            'originalAcquisitionSelector': '/utc',
                            'stagingSnapshotIsNotNewOriginalAcquisition': True,
                            'nativeDeclarationEvidence': 'Prior scoped structural/currency checks '
                                                         'bound in metadataValidation; '
                                                         'declarations are reviewed code '
                                                         'annotations, not newly read source '
                                                         'cells.',
                            'recordedSourceCoordinateDeclarations': {'title': '/title',
                                                                     'publication': '/publication',
                                                                     'scopeLimit': '/limits/0'},
                            'sourceCoordinateStatus': 'EXISTING_STAGED_SELECTOR_DECLARATIONS_NOT_REPLAYED_OR_ACCEPTED',
                            'sourceCoordinateExtent': 'Examples for retained first record only, '
                                                      'not all-record field-origin qualification. '
                                                      'Missing coordinates are explicit null.',
                            'rightsAndScopeAcceptance': 'Holds retained. No SourceContract, source '
                                                        'use, real dataset STAGING acceptance or '
                                                        'country completion installed.',
                            'acquiredAtStatus': 'source-receipt-utc-as-recorded',
                            'countryTypeApplicability': {'ingredients': {'state': 'missing-ingredient-source',
                                                                         'accepted': False,
                                                                         'scopeEvidence': 'Existing '
                                                                                          'country '
                                                                                          'category-coverage-and-gaps.json '
                                                                                          'at3829; '
                                                                                          'no new '
                                                                                          'category '
                                                                                          'validation '
                                                                                          'or '
                                                                                          'completion.'},
                                                         'recipes': {'state': 'missing-recipe-source',
                                                                     'accepted': False,
                                                                     'scopeEvidence': 'Existing '
                                                                                      'country '
                                                                                      'category-coverage-and-gaps.json '
                                                                                      'at3829; no '
                                                                                      'new '
                                                                                      'category '
                                                                                      'validation '
                                                                                      'or '
                                                                                      'completion.'},
                                                         'nutrition': {'state': 'reference-not-analytical-composition',
                                                                       'accepted': False,
                                                                       'scopeEvidence': 'Existing '
                                                                                        'country '
                                                                                        'category-coverage-and-gaps.json '
                                                                                        'at3829; '
                                                                                        'no new '
                                                                                        'category '
                                                                                        'validation '
                                                                                        'or '
                                                                                        'completion.'},
                                                         'retailers/providers': {'state': 'missing-provider-source',
                                                                                 'accepted': False,
                                                                                 'scopeEvidence': 'Existing '
                                                                                                  'country '
                                                                                                  'category-coverage-and-gaps.json '
                                                                                                  'at3829; '
                                                                                                  'no '
                                                                                                  'new '
                                                                                                  'category '
                                                                                                  'validation '
                                                                                                  'or '
                                                                                                  'completion.'},
                                                         'prices/baskets': {'state': 'missing-price-source',
                                                                            'accepted': False,
                                                                            'scopeEvidence': 'Existing '
                                                                                             'country '
                                                                                             'category-coverage-and-gaps.json '
                                                                                             'at3829; '
                                                                                             'no '
                                                                                             'new '
                                                                                             'category '
                                                                                             'validation '
                                                                                             'or '
                                                                                             'completion.'},
                                                         'dietary references': {'state': 'held-commercial-bibliographic-scope',
                                                                                'accepted': False,
                                                                                'scopeEvidence': 'Existing '
                                                                                                 'country '
                                                                                                 'category-coverage-and-gaps.json '
                                                                                                 'at3829; '
                                                                                                 'no '
                                                                                                 'new '
                                                                                                 'category '
                                                                                                 'validation '
                                                                                                 'or '
                                                                                                 'completion.'}}},
               'expected_values': {'reportCountry': 'BN', 'structuralFailuresInCountryReport': 0}},
              {'source_id': 'portfolio16-bi-best-outlook-menu',
               'country': 'BI',
               'release_id': 'publisher-restaurant-menu-snapshot20261016',
               'metadata_path': 'BI/deliverable-validation.json',
               'metadata_sha256': 'f48d11366cd4d222a987e8aa3acbe1d9db9228b396eea325ea2e69390d5c5ccf',
               'metadata_bytes': 90994,
               'original_acquired_at': '2026-10-15T22:24:37.463832+00:00',
               'last_validated_pointer': '/recordedUTC',
               'selectors': {'reportCountry': '/country',
                             'observationsInCountryReport': '/measured/observationRows',
                             'structuralFailuresInCountryReport': '/measured/failedChecks'},
               'declarations': {'countryApplicability': 'BI',
                                'dataType': 'menu-price',
                                'nativeUnitDeclaration': 'BIF',
                                'nativeBasisDeclaration': None,
                                'taxTreatment': None,
                                'serviceTreatment': None,
                                'sourceDatasetAccepted': False},
               'holds': ['tax-and-service-treatment-unknown',
                         'commercial-derivative-use-unqualified'],
               'evidence': {'retainedStagedAsset': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/BI/menu-observations.json',
                                                    'bytes': 105123,
                                                    'sha256': 'f8ec66fccb2e516ba62233827bf8cc850a08259dbf3d44d66f8442809505096b'},
                            'retainedManifest': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/manifest.json',
                                                 'bytes': 25064,
                                                 'sha256': 'ce3a3ce71137d04d10e69dffeba04f39c72c1caff02006f71d4fa0c72d6af357'},
                            'countryResultManifest': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/batch-result.json',
                                                      'bytes': 5056,
                                                      'sha256': '899a05000ad486a1c71ed50bdbc62dd59c88fd7ad2bf2f89b6eb172fb479d609'},
                            'metadataValidation': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/BI/deliverable-validation.json',
                                                   'bytes': 90994,
                                                   'sha256': 'f48d11366cd4d222a987e8aa3acbe1d9db9228b396eea325ea2e69390d5c5ccf'},
                            'originalAcquisitionReceipt': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/BI/originals/9a8d8abdb4fdf6901143/receipt.json',
                                                           'bytes': 1177,
                                                           'sha256': '4208cb309b3647b16f40d82e894206663b23a298e91b4c44b805adeda5d546e9'},
                            'originalAcquisitionSelector': '/utc',
                            'stagingSnapshotIsNotNewOriginalAcquisition': True,
                            'nativeDeclarationEvidence': 'Prior scoped structural/currency checks '
                                                         'bound in metadataValidation; '
                                                         'declarations are reviewed code '
                                                         'annotations, not newly read source '
                                                         'cells.',
                            'recordedSourceCoordinateDeclarations': {'priceLexical': '/records/0/sourcePrice/raw',
                                                                     'unitCode': '/records/0/sourcePrice/currency',
                                                                     'basis': '/records/0/sourcePrice/portionBasis',
                                                                     'taxService': '/records/0/sourcePrice/taxServiceBasis'},
                            'sourceCoordinateStatus': 'EXISTING_STAGED_SELECTOR_DECLARATIONS_NOT_REPLAYED_OR_ACCEPTED',
                            'sourceCoordinateExtent': 'Examples for retained first record only, '
                                                      'not all-record field-origin qualification. '
                                                      'Missing coordinates are explicit null.',
                            'rightsAndScopeAcceptance': 'Holds retained. No SourceContract, source '
                                                        'use, real dataset STAGING acceptance or '
                                                        'country completion installed.',
                            'acquiredAtStatus': 'source-receipt-utc-as-recorded',
                            'countryTypeApplicability': {'ingredients': {'state': 'menu-ingredient-description-incomplete',
                                                                         'accepted': False,
                                                                         'scopeEvidence': 'Existing '
                                                                                          'country '
                                                                                          'category-coverage-and-gaps.json '
                                                                                          'at3829; '
                                                                                          'no new '
                                                                                          'category '
                                                                                          'validation '
                                                                                          'or '
                                                                                          'completion.'},
                                                         'recipes': {'state': 'missing-complete-recipe',
                                                                     'accepted': False,
                                                                     'scopeEvidence': 'Existing '
                                                                                      'country '
                                                                                      'category-coverage-and-gaps.json '
                                                                                      'at3829; no '
                                                                                      'new '
                                                                                      'category '
                                                                                      'validation '
                                                                                      'or '
                                                                                      'completion.'},
                                                         'nutrition': {'state': 'policy-not-analytical-composition',
                                                                       'accepted': False,
                                                                       'scopeEvidence': 'Existing '
                                                                                        'country '
                                                                                        'category-coverage-and-gaps.json '
                                                                                        'at3829; '
                                                                                        'no new '
                                                                                        'category '
                                                                                        'validation '
                                                                                        'or '
                                                                                        'completion.'},
                                                         'retailers/providers': {'state': 'single-merchant-not-provider-register',
                                                                                 'accepted': False,
                                                                                 'scopeEvidence': 'Existing '
                                                                                                  'country '
                                                                                                  'category-coverage-and-gaps.json '
                                                                                                  'at3829; '
                                                                                                  'no '
                                                                                                  'new '
                                                                                                  'category '
                                                                                                  'validation '
                                                                                                  'or '
                                                                                                  'completion.'},
                                                         'prices/baskets': {'state': 'held-tax-service-and-reuse',
                                                                            'accepted': False,
                                                                            'scopeEvidence': 'Existing '
                                                                                             'country '
                                                                                             'category-coverage-and-gaps.json '
                                                                                             'at3829; '
                                                                                             'no '
                                                                                             'new '
                                                                                             'category '
                                                                                             'validation '
                                                                                             'or '
                                                                                             'completion.'},
                                                         'dietary references': {'state': 'held-policy-reference-scope',
                                                                                'accepted': False,
                                                                                'scopeEvidence': 'Existing '
                                                                                                 'country '
                                                                                                 'category-coverage-and-gaps.json '
                                                                                                 'at3829; '
                                                                                                 'no '
                                                                                                 'new '
                                                                                                 'category '
                                                                                                 'validation '
                                                                                                 'or '
                                                                                                 'completion.'}}},
               'expected_values': {'reportCountry': 'BI', 'structuralFailuresInCountryReport': 0}},
              {'source_id': 'portfolio16-bi-faolex-policy',
               'country': 'BI',
               'release_id': 'FAOLEX-bur211675-finite-document-snapshot20261016',
               'metadata_path': 'BI/deliverable-validation.json',
               'metadata_sha256': 'f48d11366cd4d222a987e8aa3acbe1d9db9228b396eea325ea2e69390d5c5ccf',
               'metadata_bytes': 90994,
               'original_acquired_at': '2026-10-15T22:18:50.728350+00:00',
               'last_validated_pointer': '/recordedUTC',
               'selectors': {'reportCountry': '/country',
                             'observationsInCountryReport': '/measured/observationRows',
                             'structuralFailuresInCountryReport': '/measured/failedChecks'},
               'declarations': {'countryApplicability': 'BI',
                                'dataType': 'dietary-policy-reference',
                                'nativeUnitDeclaration': None,
                                'nativeBasisDeclaration': None,
                                'taxTreatment': None,
                                'serviceTreatment': None,
                                'sourceDatasetAccepted': False},
               'holds': ['policy-not-nutrient-composition', 'reuse-and-target-scope-unqualified'],
               'evidence': {'retainedStagedAsset': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/BI/nutrition-dietary-reference.json',
                                                    'bytes': 1178,
                                                    'sha256': '6c84d85501e8814566540087d20eeb1344b9599a46affc0f7c24369215806730'},
                            'retainedManifest': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/manifest.json',
                                                 'bytes': 25064,
                                                 'sha256': 'ce3a3ce71137d04d10e69dffeba04f39c72c1caff02006f71d4fa0c72d6af357'},
                            'countryResultManifest': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/batch-result.json',
                                                      'bytes': 5056,
                                                      'sha256': '899a05000ad486a1c71ed50bdbc62dd59c88fd7ad2bf2f89b6eb172fb479d609'},
                            'metadataValidation': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/BI/deliverable-validation.json',
                                                   'bytes': 90994,
                                                   'sha256': 'f48d11366cd4d222a987e8aa3acbe1d9db9228b396eea325ea2e69390d5c5ccf'},
                            'originalAcquisitionReceipt': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/BI/originals/a91b1350d49a2ec2d551/receipt.json',
                                                           'bytes': 1242,
                                                           'sha256': '86b028380249cf1d68fa7dbe789ba4fbeb0b42de0861fe1b325155ee173661ae'},
                            'originalAcquisitionSelector': '/utc',
                            'stagingSnapshotIsNotNewOriginalAcquisition': True,
                            'nativeDeclarationEvidence': 'Prior scoped structural/currency checks '
                                                         'bound in metadataValidation; '
                                                         'declarations are reviewed code '
                                                         'annotations, not newly read source '
                                                         'cells.',
                            'recordedSourceCoordinateDeclarations': {},
                            'sourceCoordinateStatus': 'EXISTING_STAGED_SELECTOR_DECLARATIONS_NOT_REPLAYED_OR_ACCEPTED',
                            'sourceCoordinateExtent': 'Examples for retained first record only, '
                                                      'not all-record field-origin qualification. '
                                                      'Missing coordinates are explicit null.',
                            'rightsAndScopeAcceptance': 'Holds retained. No SourceContract, source '
                                                        'use, real dataset STAGING acceptance or '
                                                        'country completion installed.',
                            'acquiredAtStatus': 'source-receipt-utc-as-recorded',
                            'countryTypeApplicability': {'ingredients': {'state': 'menu-ingredient-description-incomplete',
                                                                         'accepted': False,
                                                                         'scopeEvidence': 'Existing '
                                                                                          'country '
                                                                                          'category-coverage-and-gaps.json '
                                                                                          'at3829; '
                                                                                          'no new '
                                                                                          'category '
                                                                                          'validation '
                                                                                          'or '
                                                                                          'completion.'},
                                                         'recipes': {'state': 'missing-complete-recipe',
                                                                     'accepted': False,
                                                                     'scopeEvidence': 'Existing '
                                                                                      'country '
                                                                                      'category-coverage-and-gaps.json '
                                                                                      'at3829; no '
                                                                                      'new '
                                                                                      'category '
                                                                                      'validation '
                                                                                      'or '
                                                                                      'completion.'},
                                                         'nutrition': {'state': 'policy-not-analytical-composition',
                                                                       'accepted': False,
                                                                       'scopeEvidence': 'Existing '
                                                                                        'country '
                                                                                        'category-coverage-and-gaps.json '
                                                                                        'at3829; '
                                                                                        'no new '
                                                                                        'category '
                                                                                        'validation '
                                                                                        'or '
                                                                                        'completion.'},
                                                         'retailers/providers': {'state': 'single-merchant-not-provider-register',
                                                                                 'accepted': False,
                                                                                 'scopeEvidence': 'Existing '
                                                                                                  'country '
                                                                                                  'category-coverage-and-gaps.json '
                                                                                                  'at3829; '
                                                                                                  'no '
                                                                                                  'new '
                                                                                                  'category '
                                                                                                  'validation '
                                                                                                  'or '
                                                                                                  'completion.'},
                                                         'prices/baskets': {'state': 'held-tax-service-and-reuse',
                                                                            'accepted': False,
                                                                            'scopeEvidence': 'Existing '
                                                                                             'country '
                                                                                             'category-coverage-and-gaps.json '
                                                                                             'at3829; '
                                                                                             'no '
                                                                                             'new '
                                                                                             'category '
                                                                                             'validation '
                                                                                             'or '
                                                                                             'completion.'},
                                                         'dietary references': {'state': 'held-policy-reference-scope',
                                                                                'accepted': False,
                                                                                'scopeEvidence': 'Existing '
                                                                                                 'country '
                                                                                                 'category-coverage-and-gaps.json '
                                                                                                 'at3829; '
                                                                                                 'no '
                                                                                                 'new '
                                                                                                 'category '
                                                                                                 'validation '
                                                                                                 'or '
                                                                                                 'completion.'}}},
               'expected_values': {'reportCountry': 'BI', 'structuralFailuresInCountryReport': 0}},
              {'source_id': 'portfolio16-bj-food-guide',
               'country': 'BJ',
               'release_id': 'FAO-declared-Benin-guidelines-2015',
               'metadata_path': 'BJ/deliverable-validation.json',
               'metadata_sha256': 'e4ce674f55bd11c697ec76c2e3200ac9b21b69ad2431a30bbc0f693f02b1466b',
               'metadata_bytes': 130490,
               'original_acquired_at': '2026-10-15T22:20:53.279728+00:00',
               'last_validated_pointer': '/recordedUTC',
               'selectors': {'reportCountry': '/country',
                             'observationsInCountryReport': '/measured/observationRows',
                             'structuralFailuresInCountryReport': '/measured/failedChecks'},
               'declarations': {'countryApplicability': 'BJ',
                                'dataType': 'dietary-reference',
                                'nativeUnitDeclaration': None,
                                'nativeBasisDeclaration': None,
                                'taxTreatment': None,
                                'serviceTreatment': None,
                                'sourceDatasetAccepted': False},
               'holds': ['population-and-numeric-target-scope-unqualified',
                         '2021-booklet-license-not-transferable'],
               'evidence': {'retainedStagedAsset': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/BJ/nutrition-dietary-reference.json',
                                                    'bytes': 1385,
                                                    'sha256': 'cb95e005c967736b6b03235a883c49e51936c670e8f1ba2afaaad163c7b76b03'},
                            'retainedManifest': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/manifest.json',
                                                 'bytes': 25064,
                                                 'sha256': 'ce3a3ce71137d04d10e69dffeba04f39c72c1caff02006f71d4fa0c72d6af357'},
                            'countryResultManifest': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/batch-result.json',
                                                      'bytes': 5056,
                                                      'sha256': '899a05000ad486a1c71ed50bdbc62dd59c88fd7ad2bf2f89b6eb172fb479d609'},
                            'metadataValidation': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/BJ/deliverable-validation.json',
                                                   'bytes': 130490,
                                                   'sha256': 'e4ce674f55bd11c697ec76c2e3200ac9b21b69ad2431a30bbc0f693f02b1466b'},
                            'originalAcquisitionReceipt': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/BJ/originals/8dc0b499d7bb65b6bcb4/receipt.json',
                                                           'bytes': 1342,
                                                           'sha256': '20f26f6ce3ea2a6fe10da051001f916fb372c093e62bcc69bf279cecff0e4728'},
                            'originalAcquisitionSelector': '/utc',
                            'stagingSnapshotIsNotNewOriginalAcquisition': True,
                            'nativeDeclarationEvidence': 'Prior scoped structural/currency checks '
                                                         'bound in metadataValidation; '
                                                         'declarations are reviewed code '
                                                         'annotations, not newly read source '
                                                         'cells.',
                            'recordedSourceCoordinateDeclarations': {'title': '/title',
                                                                     'publication': '/publication',
                                                                     'scopeLimit': '/limits/0'},
                            'sourceCoordinateStatus': 'EXISTING_STAGED_SELECTOR_DECLARATIONS_NOT_REPLAYED_OR_ACCEPTED',
                            'sourceCoordinateExtent': 'Examples for retained first record only, '
                                                      'not all-record field-origin qualification. '
                                                      'Missing coordinates are explicit null.',
                            'rightsAndScopeAcceptance': 'Holds retained. No SourceContract, source '
                                                        'use, real dataset STAGING acceptance or '
                                                        'country completion installed.',
                            'acquiredAtStatus': 'source-receipt-utc-as-recorded',
                            'countryTypeApplicability': {'ingredients': {'state': 'partial-original-ingredient-expressions',
                                                                         'accepted': False,
                                                                         'scopeEvidence': 'Existing '
                                                                                          'country '
                                                                                          'category-coverage-and-gaps.json '
                                                                                          'at3829; '
                                                                                          'no new '
                                                                                          'category '
                                                                                          'validation '
                                                                                          'or '
                                                                                          'completion.'},
                                                         'recipes': {'state': 'held-117-article-snapshot-120-heading',
                                                                     'accepted': False,
                                                                     'scopeEvidence': 'Existing '
                                                                                      'country '
                                                                                      'category-coverage-and-gaps.json '
                                                                                      'at3829; no '
                                                                                      'new '
                                                                                      'category '
                                                                                      'validation '
                                                                                      'or '
                                                                                      'completion.'},
                                                         'nutrition': {'state': 'guide-not-analytical-composition',
                                                                       'accepted': False,
                                                                       'scopeEvidence': 'Existing '
                                                                                        'country '
                                                                                        'category-coverage-and-gaps.json '
                                                                                        'at3829; '
                                                                                        'no new '
                                                                                        'category '
                                                                                        'validation '
                                                                                        'or '
                                                                                        'completion.'},
                                                         'retailers/providers': {'state': 'missing-provider-source',
                                                                                 'accepted': False,
                                                                                 'scopeEvidence': 'Existing '
                                                                                                  'country '
                                                                                                  'category-coverage-and-gaps.json '
                                                                                                  'at3829; '
                                                                                                  'no '
                                                                                                  'new '
                                                                                                  'category '
                                                                                                  'validation '
                                                                                                  'or '
                                                                                                  'completion.'},
                                                         'prices/baskets': {'state': 'missing-price-source',
                                                                            'accepted': False,
                                                                            'scopeEvidence': 'Existing '
                                                                                             'country '
                                                                                             'category-coverage-and-gaps.json '
                                                                                             'at3829; '
                                                                                             'no '
                                                                                             'new '
                                                                                             'category '
                                                                                             'validation '
                                                                                             'or '
                                                                                             'completion.'},
                                                         'dietary references': {'state': 'held-guide-population-target-scope',
                                                                                'accepted': False,
                                                                                'scopeEvidence': 'Existing '
                                                                                                 'country '
                                                                                                 'category-coverage-and-gaps.json '
                                                                                                 'at3829; '
                                                                                                 'no '
                                                                                                 'new '
                                                                                                 'category '
                                                                                                 'validation '
                                                                                                 'or '
                                                                                                 'completion.'}}},
               'expected_values': {'reportCountry': 'BJ', 'structuralFailuresInCountryReport': 0}},
              {'source_id': 'portfolio16-bj-fongbe-recipes',
               'country': 'BJ',
               'release_id': 'publisher-recipes-page-snapshot20261016',
               'metadata_path': 'BJ/deliverable-validation.json',
               'metadata_sha256': 'e4ce674f55bd11c697ec76c2e3200ac9b21b69ad2431a30bbc0f693f02b1466b',
               'metadata_bytes': 130490,
               'original_acquired_at': '2026-10-15T22:25:17.751654+00:00',
               'last_validated_pointer': '/recordedUTC',
               'selectors': {'reportCountry': '/country',
                             'observationsInCountryReport': '/measured/observationRows',
                             'structuralFailuresInCountryReport': '/measured/failedChecks'},
               'declarations': {'countryApplicability': 'BJ',
                                'dataType': 'recipe-expression',
                                'nativeUnitDeclaration': None,
                                'nativeBasisDeclaration': None,
                                'taxTreatment': None,
                                'serviceTreatment': None,
                                'sourceDatasetAccepted': False},
               'holds': ['commercial-reuse-and-authenticity-unqualified',
                         'servings-unit-basis-not-normalized',
                         '117-retained-120-heading-not-equivalent'],
               'evidence': {'retainedStagedAsset': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/BJ/recipe-observations.json',
                                                    'bytes': 186032,
                                                    'sha256': 'bbaf699a07d2029e01aec9ed6096d6b2f28b0e985a2f72b140e2b06e542683b4'},
                            'retainedManifest': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/manifest.json',
                                                 'bytes': 25064,
                                                 'sha256': 'ce3a3ce71137d04d10e69dffeba04f39c72c1caff02006f71d4fa0c72d6af357'},
                            'countryResultManifest': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/batch-result.json',
                                                      'bytes': 5056,
                                                      'sha256': '899a05000ad486a1c71ed50bdbc62dd59c88fd7ad2bf2f89b6eb172fb479d609'},
                            'metadataValidation': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/BJ/deliverable-validation.json',
                                                   'bytes': 130490,
                                                   'sha256': 'e4ce674f55bd11c697ec76c2e3200ac9b21b69ad2431a30bbc0f693f02b1466b'},
                            'originalAcquisitionReceipt': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/BJ/originals/14e1d0f3881da1ca945c/receipt.json',
                                                           'bytes': 1183,
                                                           'sha256': '1b26623611bdc5293afd3ebe4c9a95996ee87baecd68dd68194b3200b7c996c0'},
                            'originalAcquisitionSelector': '/utc',
                            'stagingSnapshotIsNotNewOriginalAcquisition': True,
                            'nativeDeclarationEvidence': 'Prior scoped structural/currency checks '
                                                         'bound in metadataValidation; '
                                                         'declarations are reviewed code '
                                                         'annotations, not newly read source '
                                                         'cells.',
                            'recordedSourceCoordinateDeclarations': {'ingredientExpression': '/records/0/ingredientExpressionsOriginal/0',
                                                                     'servings': '/records/0/servings'},
                            'sourceCoordinateStatus': 'EXISTING_STAGED_SELECTOR_DECLARATIONS_NOT_REPLAYED_OR_ACCEPTED',
                            'sourceCoordinateExtent': 'Examples for retained first record only, '
                                                      'not all-record field-origin qualification. '
                                                      'Missing coordinates are explicit null.',
                            'rightsAndScopeAcceptance': 'Holds retained. No SourceContract, source '
                                                        'use, real dataset STAGING acceptance or '
                                                        'country completion installed.',
                            'acquiredAtStatus': 'source-receipt-utc-as-recorded',
                            'countryTypeApplicability': {'ingredients': {'state': 'partial-original-ingredient-expressions',
                                                                         'accepted': False,
                                                                         'scopeEvidence': 'Existing '
                                                                                          'country '
                                                                                          'category-coverage-and-gaps.json '
                                                                                          'at3829; '
                                                                                          'no new '
                                                                                          'category '
                                                                                          'validation '
                                                                                          'or '
                                                                                          'completion.'},
                                                         'recipes': {'state': 'held-117-article-snapshot-120-heading',
                                                                     'accepted': False,
                                                                     'scopeEvidence': 'Existing '
                                                                                      'country '
                                                                                      'category-coverage-and-gaps.json '
                                                                                      'at3829; no '
                                                                                      'new '
                                                                                      'category '
                                                                                      'validation '
                                                                                      'or '
                                                                                      'completion.'},
                                                         'nutrition': {'state': 'guide-not-analytical-composition',
                                                                       'accepted': False,
                                                                       'scopeEvidence': 'Existing '
                                                                                        'country '
                                                                                        'category-coverage-and-gaps.json '
                                                                                        'at3829; '
                                                                                        'no new '
                                                                                        'category '
                                                                                        'validation '
                                                                                        'or '
                                                                                        'completion.'},
                                                         'retailers/providers': {'state': 'missing-provider-source',
                                                                                 'accepted': False,
                                                                                 'scopeEvidence': 'Existing '
                                                                                                  'country '
                                                                                                  'category-coverage-and-gaps.json '
                                                                                                  'at3829; '
                                                                                                  'no '
                                                                                                  'new '
                                                                                                  'category '
                                                                                                  'validation '
                                                                                                  'or '
                                                                                                  'completion.'},
                                                         'prices/baskets': {'state': 'missing-price-source',
                                                                            'accepted': False,
                                                                            'scopeEvidence': 'Existing '
                                                                                             'country '
                                                                                             'category-coverage-and-gaps.json '
                                                                                             'at3829; '
                                                                                             'no '
                                                                                             'new '
                                                                                             'category '
                                                                                             'validation '
                                                                                             'or '
                                                                                             'completion.'},
                                                         'dietary references': {'state': 'held-guide-population-target-scope',
                                                                                'accepted': False,
                                                                                'scopeEvidence': 'Existing '
                                                                                                 'country '
                                                                                                 'category-coverage-and-gaps.json '
                                                                                                 'at3829; '
                                                                                                 'no '
                                                                                                 'new '
                                                                                                 'category '
                                                                                                 'validation '
                                                                                                 'or '
                                                                                                 'completion.'}}},
               'expected_values': {'reportCountry': 'BJ', 'structuralFailuresInCountryReport': 0}},
              {'source_id': 'portfolio16-bl-pablo-menu',
               'country': 'BL',
               'release_id': 'retained-owner44-private-menu-slice-edition-unknown',
               'metadata_path': 'BL/deliverable-validation.json',
               'metadata_sha256': '727e1f4b2ce7eccff61f81330b9a87fb89b9694b2d48073e1043cb15e9fd8735',
               'metadata_bytes': 10498,
               'original_acquired_at': None,
               'last_validated_pointer': '/recordedUTC',
               'selectors': {'reportCountry': '/country',
                             'observationsInCountryReport': '/measured/observationRows',
                             'structuralFailuresInCountryReport': '/measured/failedChecks'},
               'declarations': {'countryApplicability': 'BL',
                                'dataType': 'menu-price',
                                'nativeUnitDeclaration': 'EUR',
                                'nativeBasisDeclaration': None,
                                'taxTreatment': None,
                                'serviceTreatment': 'included-as-recorded-in-retained-coverage',
                                'sourceDatasetAccepted': False},
               'holds': ['edition-and-currentness-unknown',
                         'quantities-and-derivative-use-unqualified'],
               'evidence': {'retainedStagedAsset': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/BL/menu-observations.json',
                                                    'bytes': 11901,
                                                    'sha256': '0b58d0a7feb3c1239eb48dd8da7ce462faa98b24e1a3ea20a5dfb942b45ae18b'},
                            'retainedManifest': {'path': '/home/user/src/offmenu-data/country-bundles-20261016/owner-16/manifest.json',
                                                 'bytes': 25064,
                                                 'sha256': 'ce3a3ce71137d04d10e69dffeba04f39c72c1caff02006f71d4fa0c72d6af357'},
                            'countryResultManifest': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/batch-result.json',
                                                      'bytes': 5056,
                                                      'sha256': '899a05000ad486a1c71ed50bdbc62dd59c88fd7ad2bf2f89b6eb172fb479d609'},
                            'metadataValidation': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/BL/deliverable-validation.json',
                                                   'bytes': 10498,
                                                   'sha256': '727e1f4b2ce7eccff61f81330b9a87fb89b9694b2d48073e1043cb15e9fd8735'},
                            'originalAcquisitionReceipt': None,
                            'originalAcquisitionSelector': None,
                            'stagingSnapshotIsNotNewOriginalAcquisition': True,
                            'nativeDeclarationEvidence': 'Prior scoped structural/currency checks '
                                                         'bound in metadataValidation; '
                                                         'declarations are reviewed code '
                                                         'annotations, not newly read source '
                                                         'cells.',
                            'recordedSourceCoordinateDeclarations': {'priceLexical': '/rows/0/sourcePrice/raw',
                                                                     'unitCode': '/rows/0/sourcePrice/currency',
                                                                     'basis': None,
                                                                     'taxService': None},
                            'sourceCoordinateStatus': 'EXISTING_STAGED_SELECTOR_DECLARATIONS_NOT_REPLAYED_OR_ACCEPTED',
                            'sourceCoordinateExtent': 'Examples for retained first record only, '
                                                      'not all-record field-origin qualification. '
                                                      'Missing coordinates are explicit null.',
                            'rightsAndScopeAcceptance': 'Holds retained. No SourceContract, source '
                                                        'use, real dataset STAGING acceptance or '
                                                        'country completion installed.',
                            'acquiredAtStatus': 'UNKNOWN_NOT_INFERRED_FROM_VALIDATION_DATE',
                            'countryTypeApplicability': {'ingredients': {'state': 'partial-menu-description-not-quantities',
                                                                         'accepted': False,
                                                                         'scopeEvidence': 'Existing '
                                                                                          'country '
                                                                                          'category-coverage-and-gaps.json '
                                                                                          'at3829; '
                                                                                          'no new '
                                                                                          'category '
                                                                                          'validation '
                                                                                          'or '
                                                                                          'completion.'},
                                                         'recipes': {'state': 'missing-complete-recipe',
                                                                     'accepted': False,
                                                                     'scopeEvidence': 'Existing '
                                                                                      'country '
                                                                                      'category-coverage-and-gaps.json '
                                                                                      'at3829; no '
                                                                                      'new '
                                                                                      'category '
                                                                                      'validation '
                                                                                      'or '
                                                                                      'completion.'},
                                                         'nutrition': {'state': 'missing-nutrient-source',
                                                                       'accepted': False,
                                                                       'scopeEvidence': 'Existing '
                                                                                        'country '
                                                                                        'category-coverage-and-gaps.json '
                                                                                        'at3829; '
                                                                                        'no new '
                                                                                        'category '
                                                                                        'validation '
                                                                                        'or '
                                                                                        'completion.'},
                                                         'retailers/providers': {'state': 'single-merchant-not-provider-register',
                                                                                 'accepted': False,
                                                                                 'scopeEvidence': 'Existing '
                                                                                                  'country '
                                                                                                  'category-coverage-and-gaps.json '
                                                                                                  'at3829; '
                                                                                                  'no '
                                                                                                  'new '
                                                                                                  'category '
                                                                                                  'validation '
                                                                                                  'or '
                                                                                                  'completion.'},
                                                         'prices/baskets': {'state': 'held-edition-currentness-and-quantities',
                                                                            'accepted': False,
                                                                            'scopeEvidence': 'Existing '
                                                                                             'country '
                                                                                             'category-coverage-and-gaps.json '
                                                                                             'at3829; '
                                                                                             'no '
                                                                                             'new '
                                                                                             'category '
                                                                                             'validation '
                                                                                             'or '
                                                                                             'completion.'},
                                                         'dietary references': {'state': 'missing-qualified-guide-or-allergen-list',
                                                                                'accepted': False,
                                                                                'scopeEvidence': 'Existing '
                                                                                                 'country '
                                                                                                 'category-coverage-and-gaps.json '
                                                                                                 'at3829; '
                                                                                                 'no '
                                                                                                 'new '
                                                                                                 'category '
                                                                                                 'validation '
                                                                                                 'or '
                                                                                                 'completion.'}},
                            'serviceDeclarationEvidence': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16/BL/category-coverage-and-gaps.json',
                                                           'sha256': '2b139dfb2e204a812c03349ed1bbe3b12d8e42f5f01b3e825db74361940bd89a',
                                                           'selector': '/categories/4/scopeAndGap',
                                                           'recordedScope': 'Selected EUR menu '
                                                                            'prices/service '
                                                                            'included; '
                                                                            'edition/current '
                                                                            'availability '
                                                                            'unqualified',
                                                           'meaning': 'Retained coverage '
                                                                      'statement, not newly '
                                                                      'checked original menu or '
                                                                      'inferred tax treatment.'}},
               'expected_values': {'reportCountry': 'BL', 'structuralFailuresInCountryReport': 0}}]}

"""Reviewed Worker18 declarations; historical metadata, no data admission."""

BINDINGS = {'schemaVersion': 'offmenu-portfolio18-catalogue/1',
 'worker': 18,
 'baseCommit': 'abecb99ee1125730ccbc2824b6ec49ffc5cc4302',
 'countryComplete': False,
 'requiredDomains': ['ingredients',
                     'recipes',
                     'nutrition',
                     'retailers/providers',
                     'prices/baskets',
                     'dietaryreferences'],
 'allCountryDomainCellsIncomplete': True,
 'separateHeldSources': {'BS-BahamaBites': 'Retained18pages; private download does not grant '
                                           'recipe/image derivation; publisher/custodian50 '
                                           'use/edition/selectors missing',
                         'BS-FAO2002': 'Launch profile does not establish underlying '
                                       'edition/rights/current advice',
                         'BR-other': 'Embrapa STOP; TBCA/ANVISA restrictions and export budget '
                                     'remain separate'},
 'overlap': {'BR': '31IDs461source coordinates union;88 shared cells, not39foods549cells',
             'otherWorkers': '25 reviews,57 NL adapter,64 continuation/sync; source '
                             'custodians49/50; no duplicate acquisition'},
 'bindings': {'BO-zenodo-metadata': {'bindingId': 'BO-zenodo-metadata',
                                     'country': 'BO',
                                     'sourceId': 'zenodo-17295428',
                                     'releaseId': 'published-2025-10-08',
                                     'domains': ['dietaryreferences'],
                                     'scope': 'discovery metadata only; no Data.dta inspection',
                                     'declaredCount': {'foodRecords': 0},
                                     'inputs': {'record-17295428.json': 'f0ea2357fd91f78c016161ed8ca6f2a2227f9c9933094e96b31ebc994e4953db'},
                                     'retainedManifest': {'path': '/home/user/src/offmenu-data/originals/country-followthrough-20261015/owner-47/BO/d06c358abec9484baa1d/receipt.json',
                                                          'sha256': '0e521b8b516b5c57eb5f7539559540de7b55af1dfb63cba774fd459aa5294a9d',
                                                          'verification': 'retained historical '
                                                                          'metadata declaration; '
                                                                          'no current body read'},
                                     'fieldDeclarations': [],
                                     'nativeUnitsAndBases': {},
                                     'unknowns': ['record unit',
                                                  'dictionary',
                                                  'native units',
                                                  'safe aggregate dimensions',
                                                  'current custodian'],
                                     'holds': [{'code': 'subject-privacy-scope',
                                                'kind': 'source-use',
                                                'owner': 'Morgan and actual source custodian, '
                                                         'unestablished',
                                                'nextAction': 'Establish safe aggregate scope '
                                                              'without subject inspection'}],
                                     'dependencies': [{'code': 'dictionary-missing',
                                                       'kind': 'missing-input',
                                                       'owner': 'Actual custodian via Morgan',
                                                       'nextAction': 'Supply retained '
                                                                     'codebook/Code.do and '
                                                                     'version-matched record-unit '
                                                                     'evidence'}],
                                     'originalAcquiredAt': '2026-10-14T22:20:58.225202+00:00',
                                     'acquisitionTimeEvidence': 'receipt /requests/0/requestUTC '
                                                                'for matching metadata hash only; '
                                                                'not Data.dta time',
                                     'sourceCache': 'not opened or verified by this package',
                                     'rightsGrant': 'none conferred by this binding',
                                     'integration': 'no registered admission, parser, canonical '
                                                    'mapping or writer',
                                     'upstreamSourceSha256': 'f0ea2357fd91f78c016161ed8ca6f2a2227f9c9933094e96b31ebc994e4953db',
                                     'upstreamSourceVerification': 'historical receipt declaration '
                                                                   'only; not current source '
                                                                   'integrity check',
                                     'projectionContract': 'A future candidate must preserve both '
                                                           'retained input JSON selector and '
                                                           'upstream original coordinate; no '
                                                           'origin inferred from hash alone'},
              'BQ-cbs-coordinate': {'bindingId': 'BQ-cbs-coordinate',
                                    'country': 'BQ',
                                    'sourceId': 'cbs-bq-health',
                                    'releaseId': 'survey-2021-publication-2022-10-03',
                                    'domains': ['dietaryreferences'],
                                    'scope': 'independent38 coordinate-only PASS487; numeric '
                                             'observations not normalized',
                                    'declaredCount': {'sheets': 4,
                                                      'definitionExamples': 12,
                                                      'coordinateFields': 36,
                                                      'normalizedObservations': 0},
                                    'inputs': {'scope-contract.json': '9eb28aa129cb1e112e22c6ff6f758b019dd0224abc550f179579f2be0e5db6a0',
                                               'definition-examples.json': 'a9a024db19a72a075219d8b35e5058385fc1710a664ac04edc63443cfef1121a',
                                               'explanatory-evidence.json': 'bc24baf8419576f06a1ccc29710560cb848ff3355e0922c478e24c1325f842a6',
                                               'header-map.json': '3a3f333fae5c3db80111de4b5afcbeb89fd59bd574861d9b86d695a8d891a0f2'},
                                    'retainedManifest': {'path': '/home/user/src/offmenu-data/country-bundle-20261016/owner-18/delta05-CBS-source-coordinate-contract/manifest.json',
                                                         'sha256': '9460e1f2ebaeaef78b7aa08f747539747925ea885d5a80efdef10ba00b470cdb',
                                                         'verification': 'retained historical '
                                                                         'metadata declaration; no '
                                                                         'current body read'},
                                    'fieldDeclarations': [{'input': 'header-map.json',
                                                           'selector': 'source workbook sheet plus '
                                                                       'cell coordinate as '
                                                                       'declared in retained '
                                                                       'header map',
                                                           'meaning': 'locator only; no numeric '
                                                                      'conversion'},
                                                          {'input': 'definition-examples.json',
                                                           'selector': '12 retained definition '
                                                                       'examples; each original '
                                                                       'cell coordinate retained',
                                                           'meaning': 'definition evidence; '
                                                                      'population_override remains '
                                                                      'null'}],
                                    'nativeUnitsAndBases': {'percentage': 'only where explicitly '
                                                                          'labelled',
                                                            'plain schatting': None,
                                                            'dot': '<50 observations, not zero',
                                                            'zero': 'sample zero, not population '
                                                                    'absence'},
                                    'unknowns': ['topic denominators',
                                                 'eligibility/minimum age',
                                                 'sample weights',
                                                 'plain schatting unit',
                                                 'blank AT5 semantics',
                                                 'Fruit A57/C57 label-definition conflict',
                                                 'acquiredAt'],
                                    'holds': [{'code': 'survey-semantics-unresolved',
                                               'kind': 'source-use',
                                               'owner': 'CBS publisher; Morgan routes prepared '
                                                        'questions',
                                               'nextAction': 'Obtain version-matched methods and '
                                                             'Fruit erratum; no normalization'},
                                              {'code': 'document-exception-review',
                                               'kind': 'source-use',
                                               'owner': 'Source-use reviewer',
                                               'nextAction': 'Resolve applicable CC-BY '
                                                             'attribution/document exceptions'}],
                                    'dependencies': [{'code': 'canonical-writer-unbound',
                                                      'kind': 'integration',
                                                      'owner': 'Integrator00',
                                                      'nextAction': 'Review source-native '
                                                                    'coordinate contract before '
                                                                    'any candidate projection'}],
                                    'originalAcquiredAt': None,
                                    'acquisitionTimeEvidence': 'unknown',
                                    'sourceCache': 'not opened or verified by this package',
                                    'rightsGrant': 'none conferred by this binding',
                                    'integration': 'no registered admission, parser, canonical '
                                                   'mapping or writer',
                                    'upstreamSourceSha256': 'ede5664dafd9317ccbdf54ec215e19290b65155a1e7847e72142c4bba3bdaa68',
                                    'upstreamSourceVerification': 'historical receipt declaration '
                                                                  'only; not current source '
                                                                  'integrity check',
                                    'projectionContract': 'A future candidate must preserve both '
                                                          'retained input JSON selector and '
                                                          'upstream original coordinate; no origin '
                                                          'inferred from hash alone'},
              'BR-taco4-literals': {'bindingId': 'BR-taco4-literals',
                                    'country': 'BR',
                                    'sourceId': 'nepa-unicamp-taco',
                                    'releaseId': '4-revised-2011',
                                    'domains': ['nutrition'],
                                    'scope': 'independent38 private literal PASS3048/bound3050; '
                                             'exactly source IDs1..8, physical29/30 printed26/27',
                                    'declaredCount': {'foodIds': 8,
                                                      'literalCells': 208,
                                                      'numericLiterals': 156,
                                                      'NA': 16,
                                                      'Tr': 14,
                                                      'blank': 22},
                                    'inputs': {'first8-source-literals.json': 'f75112a8456803e2250454c4216a7a00f2fefe79eb710f46adab1bdc8acdf2f7'},
                                    'retainedManifest': {'path': '/home/user/Documents/Codex/2026-10-13/task-3/reports/country-delivery-priority-20261017/owner-18/BR-TACO4-first8-literals-v1/manifest.json',
                                                         'sha256': 'b0e02e679071038cfddc0f926640582206e66e76f0849bb10e811ad080700ea0',
                                                         'verification': 'retained metadata pin; '
                                                                         'no current source-body '
                                                                         'read'},
                                    'fieldDeclarations': [{'input': 'first8-source-literals.json',
                                                           'selector': 'records[*].source_record_id',
                                                           'meaning': 'source food ID1..8, not '
                                                                      'canonical ID'},
                                                          {'input': 'first8-source-literals.json',
                                                           'selector': 'records[*].cells[*].value_literal',
                                                           'originSelector': 'records[*].cells[*].coordinate',
                                                           'meaning': 'column_id p29:c1..11 or '
                                                                      'p30:c1..15; original '
                                                                      'source_words and coordinate '
                                                                      'retained; numeric_value '
                                                                      'null'},
                                                          {'input': 'first8-source-literals.json',
                                                           'selector': 'header column declarations '
                                                                       'and caption basis',
                                                           'meaning': 'Portuguese header units and '
                                                                      '100g edible-portion basis; '
                                                                      'no nutrient equivalence'}],
                                    'nativeUnitsAndBases': {'headers': ['(%)',
                                                                        '(kcal)',
                                                                        '(kJ)',
                                                                        '(g)',
                                                                        '(mg)',
                                                                        '(µg)'],
                                                            'basis': '100 gramas de parte '
                                                                     'comestível',
                                                            'NA': 'source literal',
                                                            'Tr': 'source literal',
                                                            'blank': None},
                                    'unknowns': ['acquiredAt',
                                                 'accepted canonical nutrient mapping'],
                                    'holds': [{'code': 'metadata-only-current-dispatch',
                                               'kind': 'authorization',
                                               'owner': 'Morgan',
                                               'nextAction': 'Any source-body execution needs '
                                                             'separately qualified dispatch'}],
                                    'dependencies': [{'code': 'full-extent-parser-missing',
                                                      'kind': 'missing-input',
                                                      'owner': 'Worker18 under future dispatch',
                                                      'nextAction': 'Implement repeatable '
                                                                    'exact8x26 projection; '
                                                                    'old31x11 parser does not '
                                                                    'cover it'},
                                                     {'code': 'independent-integration-required',
                                                      'kind': 'integration',
                                                      'owner': 'Integrator00 and independent '
                                                               'reviewer',
                                                      'nextAction': 'Review exact manifest, '
                                                                    'source-native semantics and '
                                                                    'writer contract'}],
                                    'originalAcquiredAt': None,
                                    'acquisitionTimeEvidence': 'unknown',
                                    'sourceCache': 'not opened or verified by this package',
                                    'rightsGrant': 'none conferred by this binding',
                                    'integration': 'no registered admission, parser, canonical '
                                                   'mapping or writer',
                                    'upstreamSourceSha256': '2002aec5615b5b1395aaa8fa675635bbb7f712c33f278af5e332f1cac8f108c8',
                                    'upstreamSourceVerification': 'historical receipt declaration '
                                                                  'only; not current source '
                                                                  'integrity check',
                                    'projectionContract': 'A future candidate must preserve both '
                                                          'retained input JSON selector and '
                                                          'upstream original coordinate; no origin '
                                                          'inferred from hash alone'},
              'BS-cpi-literals': {'bindingId': 'BS-cpi-literals',
                                  'country': 'BS',
                                  'sourceId': 'bnsi-cpi',
                                  'releaseId': 'retained-2026-10-14',
                                  'domains': ['prices/baskets'],
                                  'scope': 'independent38 private literal/custody PASS; CPI index '
                                           'only, not item price',
                                  'declaredCount': {'literalObservations': 78,
                                                    'categories': 13,
                                                    'periods': 6},
                                  'inputs': {'cpi-observation-proposals.json': '16f309aad098f6477f840f634f7ebd722a2c0d1fb7fb9096d527860fe74aacdd'},
                                  'retainedManifest': {'path': '/home/user/src/offmenu-data/country-bundle-20261016/owner-18/phase1-packet.json',
                                                       'sha256': '646b798db11e1f4398b59c17786b1e65a87fdbbee4daac71b567c6911270aa04',
                                                       'verification': 'retained historical '
                                                                       'metadata declaration; no '
                                                                       'current body read'},
                                  'fieldDeclarations': [{'input': 'cpi-observation-proposals.json',
                                                         'selector': 'records[*].value_literal',
                                                         'originSelector': 'records[*].locator',
                                                         'meaning': 'HTML table_index_zero_based2, '
                                                                    'retained '
                                                                    'row_index_including_header '
                                                                    'and '
                                                                    'column_index_zero_based2..7'},
                                                        {'input': 'cpi-observation-proposals.json',
                                                         'selector': 'records[*].period_literal',
                                                         'meaning': 'source period '
                                                                    'Sep2025–Feb2026, not '
                                                                    'acquisition time'},
                                                        {'input': 'cpi-observation-proposals.json',
                                                         'selector': 'records[*].weight_literal',
                                                         'meaning': 'literal only, no '
                                                                    'renormalization'}],
                                  'nativeUnitsAndBases': {'measure': 'CPI index',
                                                          'index_base': None,
                                                          'weight_basis': None,
                                                          'source_effective_date': None},
                                  'unknowns': ['index base',
                                               '100.0 versus102.39 weight semantics',
                                               'rights acceptance',
                                               'publisher effective date',
                                               'original acquisition time'],
                                  'holds': [{'code': 'index-basis-and-use-unresolved',
                                             'kind': 'source-use',
                                             'owner': 'BNSI publisher and source-use reviewer via '
                                                      'Morgan',
                                             'nextAction': 'Resolve base/weight and use scope; no '
                                                           'arithmetic or item-price admission'}],
                                  'dependencies': [{'code': 'typed-writer-unbound',
                                                    'kind': 'integration',
                                                    'owner': 'Integrator00',
                                                    'nextAction': 'Review source-native CPI '
                                                                  'contract, not item-price '
                                                                  'projection'}],
                                  'originalAcquiredAt': None,
                                  'acquisitionTimeEvidence': 'retainedSnapshotAt is a candidate '
                                                             'declaration, not independently '
                                                             'matched original request time',
                                  'sourceCache': 'not opened or verified by this package',
                                  'rightsGrant': 'none conferred by this binding',
                                  'integration': 'no registered admission, parser, canonical '
                                                 'mapping or writer',
                                  'retainedSnapshotAt': '2026-10-14T22:11:41.072046+00:00',
                                  'upstreamSourceSha256': '3b8552b39202cc3e1eedd1fb1f361187b7c3e65bae5dc734885aaa459e28c2f3',
                                  'upstreamSourceVerification': 'historical receipt declaration '
                                                                'only; not current source '
                                                                'integrity check',
                                  'projectionContract': 'A future candidate must preserve both '
                                                        'retained input JSON selector and upstream '
                                                        'original coordinate; no origin inferred '
                                                        'from hash alone'}}}

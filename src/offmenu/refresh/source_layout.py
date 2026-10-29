"""Maintained source-layout-v2 handler routes; not dataset admission.

Historical capabilities.py and its old Git object pins stay immutable. These
current code pins bind migrated paths/imports for authored offline regression.
Old qualification fingerprints remain stale; ADMISSIONS stays empty.
"""
SOURCE_LAYOUT_VERSION = "offmenu-source-layout/2"
CURRENT_HANDLERS = {'afcd': ('tools/data-processing/import_afcd.py', '5bf7f793cbfc63b7be1c592ff68da3961bfe5c1a'),
 'ciqual': ('tools/data-processing/collect_national.py',
            '2c5b4a7cd2810dffd569ece5c780bc2718148055'),
 'cnf': ('tools/data-processing/collect_cnf.py', '14e9dba1ad15e17c6eee039d74f53e887b3cbb7d'),
 'cofid': ('tools/data-processing/import_national_tables.py',
           'fb4b6c304ff1c4f3cf28210e815c652c3635a814'),
 'fineli': ('tools/data-processing/collect_next_national.py',
            'ed5426048186bdef4eedb7b01c40c38646e1f34b'),
 'foodfiles': ('tools/data-processing/collect_next_national.py',
               'ed5426048186bdef4eedb7b01c40c38646e1f34b'),
 'foodon': ('tools/data-processing/collect_foodon_definitions.py',
            'fa232aabeb8162e2bbbd51ef71775e4b46193cb2'),
 'frida': ('tools/data-processing/collect_national.py', '2c5b4a7cd2810dffd569ece5c780bc2718148055'),
 'germany-bls': ('tools/data-processing/import_national_tables.py',
                 'fb4b6c304ff1c4f3cf28210e815c652c3635a814'),
 'matvaretabellen': ('tools/data-processing/collect_national.py',
                     '2c5b4a7cd2810dffd569ece5c780bc2718148055'),
 'mext': ('tools/data-processing/collect_mext.py', '6f10f7c76d171158be5f9042e36f5523802006e6'),
 'overture-food-places': ('tools/data-processing/collect_overture.py',
                          '831a3123936c88a6dcddffdf12486bbd83477797'),
 'qudt-measurement-definitions': ('tools/data-processing/collect_measurement_terminology_20261014.py',
                                  '24faa8b5ae676fbe4790b2d9a90c6eca4d609084'),
 'recipe-expansion-20261014': ('tools/data-processing/collect_recipe_expansion_20261014.py',
                               '4b453beb0f7e9ed6514c96ed043e87c4a7edded7'),
 'sweden-food': ('tools/data-processing/collect_next_national.py',
                 'ed5426048186bdef4eedb7b01c40c38646e1f34b'),
 'usda-files': ('tools/data-processing/normalize_usda.py',
                'a995c38c209257ed3147f43d7b8903b24de24d11'),
 'wikibooks': ('tools/data-processing/collect_wikibooks_live.py',
               '5542c028f49ba35da2171809ee74f7a64cb3e9da'),
 'wikidata-food-businesses': ('tools/data-processing/collect_business_references.py',
                              'f5ea7f7675dd31edef2a3b65122f1853f0c2e486'),
 'world-recipes': ('tools/data-processing/collect_world_recipes.py',
                   'bcb15838a15f282d1f3727911f98e776fa3565c5')}
CURRENT_NATIONAL = ('tools/data-processing/import_national_tables.py', 'fb4b6c304ff1c4f3cf28210e815c652c3635a814')

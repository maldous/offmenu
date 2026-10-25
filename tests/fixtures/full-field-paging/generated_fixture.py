"""Generated-only examples; no retained records or real provider observations."""
from offmenu.refresh.full_field_reader import FieldReader, Limits

KEY = b'synthetic-fixture-only-not-a-production-key-0000'


def binding():
    return {
        'sourceObservationReference': {
            'schema': 'offmenu-identifier-observation/2', 'databaseSha256': '1' * 64,
            'detailSelectionSha256': '2' * 64, 'runId': 'synthetic-run',
            'namespace': 'barcode', 'originalLexicalValue': 'synthetic-original',
            'sourceLexicalValue': 'synthetic-source', 'symbology': None,
            'matchType': 'synthetic-only', 'equivalence': 'not-a-product-assertion',
            'disposition': 'source-asserted', 'sourceId': 'synthetic-source',
            'releaseId': None, 'sourceRecordId': None,
            'observationKey': {'run_id': 'synthetic-run', 'input_id': 'fixture',
                               'record_ordinal': 1, 'assertion_id': 1}},
        'sourceBinding': {'representation': 'generated-only', 'sourcePointer': '/fixture/1',
                          'unknownExtension': {'keep': True}},
        'revisionSha256': '3' * 64, 'fieldPath': '/0/data/unknown~1extension',
        'selectionRevision': '2' * 64, 'generation': 7,
        'attribution': {'notice': 'Generated synthetic fixture; no upstream acquisition.',
                        'originalLanguage': None},
    }


def reader(value, *, state='present', delivery='permitted', limits=Limits(page_bytes=4096), context=None):
    extra = {} if state == 'rights-held' or delivery == 'rights-held' else {'unknownMetadata': ['kept', 'kept']}
    return FieldReader(binding=binding() if context is None else context,
        field={'state': state, 'value': value, 'fieldPointer': '/0/data/unknown~1extension',
               'evidenceSha256': '4' * 64, 'sourceFieldState': 'unknown',
               'valueOrigin': 'generated-only', 'language': None, **extra},
        delivery=delivery, cursor_key=KEY, limits=limits)

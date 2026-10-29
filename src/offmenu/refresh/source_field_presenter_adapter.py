"""Pure adapter for the frozen UI readMore callback. No HTTP/store/permission API."""
import json
from dataclasses import replace
from .full_field_reader import canonical, fail, clone, Budget


def selected_node_request(reader, *, opaque_cursor=None):
    binding = json.loads(reader._metadata)['binding']
    return {'binding': binding, 'opaqueCursor': opaque_cursor, 'generation': binding['generation']}


def read_page(reader, request):
    """Exact callback for the frozen source-field-page-presenter.js.

    Reader admission is native-only. This validates an already selected reader's
    context; client-supplied binding must never construct/select a store/reader.
    """
    budget = Budget(replace(reader._limits,
        snapshot_bytes=min(8192, reader._limits.snapshot_bytes)), reader._clock)
    request = clone(request, budget)
    if type(request) is not dict or set(request) != {'binding', 'opaqueCursor', 'generation'}:
        fail('node-request')
    if len(canonical(request)) > 8192:
        fail('request-bound')
    expected = selected_node_request(reader)
    if (canonical(request['binding']) != canonical(expected['binding'])
            or canonical(request['generation']) != canonical(expected['generation'])):
        fail('presenter-binding-mismatch')
    return reader.read(request['opaqueCursor'], _budget=budget)


def selected_request(reader, *, opaque_cursor=None):
    """Synthetic/native caller helper, not an authority validator or browser API."""
    binding = json.loads(reader._metadata)['binding']
    parts = [binding['sourceObservationReference'], binding['selectionRevision'],
             binding['sourceBinding'], binding['fieldPath'], binding['generation']]
    return dict(zip(('sourceObservationReference', 'selectionRevision', 'sourceBinding',
                     'sourcePath', 'generation'), parts),
                selectionKey=json.dumps(parts, ensure_ascii=False, separators=(',', ':')),
                opaqueCursor=opaque_cursor)


def read_more(reader, request):
    """Validate selected context before echoing its UI selectionKey.

    One backend node page becomes one explicitly labelled projection fragment.
    Do not combine fragments into a monolithic value or mistake them for products.
    """
    budget = Budget(replace(reader._limits,
        snapshot_bytes=min(8192, reader._limits.snapshot_bytes)), reader._clock)
    request = clone(request, budget)
    expected = selected_request(reader)
    keys = set(expected)
    if type(request) is not dict or set(request) != keys:
        fail('presenter-request')
    if len(canonical(request)) > 8192:
        fail('request-bound')
    if any(canonical(request[name]) != canonical(expected[name])
           for name in keys - {'selectionKey', 'opaqueCursor'}):
        fail('presenter-binding-mismatch')
    try:
        from .full_field_reader import unique_object
        supplied_key = json.loads(request['selectionKey'], object_pairs_hook=unique_object)
        expected_key = json.loads(expected['selectionKey'])
    except (TypeError, ValueError, UnicodeError):
        fail('presenter-binding-mismatch')
    if canonical(supplied_key) != canonical(expected_key):
        fail('presenter-binding-mismatch')
    budget.check()
    return reader.walk(request['opaqueCursor'], envelope=lambda page: _project_page(page, request), _budget=budget)


def _project_page(page, request):
    content, metadata = page['content'], dict(page['field'])
    state = page['state']
    value = None
    if state == 'present':
        if content['kind'] == 'text':
            value = content['text']
        elif content['kind'] in ('array', 'object'):
            value = [{'key': child['key'], 'sourceValueType': child['valueType']}
                     for child in content['children']]
        elif content['kind'] == 'number':
            value = content['jsonNumber']
        else:
            value = content['value']
    metadata.update(state='partial' if state == 'present' and not page['valueCompleteInThisPage'] else state,
                    value=value, sourceFieldDeliveryState=state, deliveryPath=page['path'],
                    sourceDescriptorState=page['field']['state'],
                    deliveryKind=content['kind'] if content else None,
                    deliveryView='node-page-fragment')
    if content and content['kind'] == 'text':
        metadata['textRange'] = {key: content[key] for key in ('start', 'end', 'total', 'offsetUnit')}
    if content and content['kind'] == 'number':
        metadata['numberKind'] = content['numberKind']
    # Existing fieldPointer is retained verbatim; display label adds escaped
    # relative path, without rewriting an original source pointer.
    label = page['binding']['fieldPath'] + ''.join('/' + str(token).replace('~', '~0').replace('/', '~1')
                                                for token in page['path'])
    result = {'selectionKey': request['selectionKey'],
        'sourceProducts': [{'sourceObservationReference': page['binding']['sourceObservationReference'],
            'sourceBinding': page['binding']['sourceBinding'], 'attribution': page['binding']['attribution'],
            'fields': {label: metadata}, 'deliveryPage': {key: page[key] for key in
                ('schema', 'snapshotSha256', 'path', 'scope', 'nodeExhausted', 'valueCompleteInThisPage')}}],
        'productDetailAvailability': [{'state': state, 'scope': 'selected-field-only'}],
        'projectionLimitations': ['One selected field snapshot only; fragments are not physical products.',
            'Traversal exhaustion does not establish original-source, population, country or gold completion.'],
        'state': 'available' if page['traversalExhausted'] and state in ('present', 'null') else 'partial',
        'hasMore': page['nextCursor'] is not None, 'nextCursor': page['nextCursor'], 'error': None}
    return result

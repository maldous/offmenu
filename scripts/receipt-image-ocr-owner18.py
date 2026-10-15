"""Caller-controlled local OCR. No uploads, logs, inventory or persistent writes."""
import csv
from datetime import date
import re
import hashlib
import io
import math
import os
from pathlib import Path
import subprocess
import tempfile

MAX_BYTES = 3 * 1024 * 1024
MAX_PIXELS = 8_000_000


def _capture(value):
    """Only bounded own plain data; reject custom mappings/objects before hooks."""
    nodes = 0
    def visit(v, depth=0):
        nonlocal nodes
        nodes += 1
        if depth > 8 or nodes > 256:
            raise ValueError('Context exceeds capture bounds')
        if v is None or type(v) in (bool, int):
            return v
        if type(v) is str and len(v) <= 2000:
            return v
        if type(v) is dict and len(v) <= 64:
            if any(type(k) is not str or len(k) > 200 for k in v):
                raise ValueError('Plain context required')
            return {k: visit(x, depth+1) for k, x in v.items()}
        raise ValueError('Plain context required')
    return visit(value)


def _recheck(captured, provider):
    # Trusted owner reads current authenticated session/consent/rights/clock.
    current = _capture(provider())
    _gate(current)
    if any(current[k] != captured[k] for k in ('accountId', 'sourceId', 'retainUntil')) or current['now'] < captured['now']:
        raise ValueError('Admission changed during extraction')


def _text(v):
    if not isinstance(v, str) or not v.strip() or len(v) > 200:
        raise ValueError('Invalid identity or field')
    return v


def _gate(context):
    now = context['now']
    if type(now) is not int or now < 0:
        raise ValueError('Invalid clock')
    for k in ('accountId', 'sourceId'):
        _text(context[k])
    if context.get('ownerConfirmed') is not True:
        raise ValueError('Explicit source ownership required')
    consent, rights = context.get('consent', {}), context.get('rights', {})
    if consent.get('accountId') != context['accountId'] or consent.get('receiptReview') is not True:
        raise ValueError('Current account consent required')
    if rights.get('sourceId') != context['sourceId'] or rights.get('privateUse') is not True:
        raise ValueError('Private source rights required')
    for v in (consent.get('expiresAt'), rights.get('expiresAt'), context.get('retainUntil')):
        if type(v) is not int or v <= now:
            raise ValueError('Expired or missing consent/rights/retention')


def local_tesseract(image):
    """Decoded image only; temporary metadata-free PNG and TSV are deleted on exit."""
    with tempfile.TemporaryDirectory(prefix='owner18-ocr-') as scratch:
        source, output = Path(scratch) / 'input.png', Path(scratch) / 'output'
        image.convert('RGB').save(source, format='PNG')
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        try:
            subprocess.run(['tesseract', str(source), str(output), '-l', 'eng', '--psm', '6', 'tsv'],
                           env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=15, check=True)
        except (OSError, subprocess.SubprocessError):
            raise ValueError('Local OCR unavailable or failed') from None
        tsv = output.with_suffix('.tsv')
        if tsv.stat().st_size > 1024 * 1024:
            raise ValueError('OCR output exceeds bound')
        tokens = []
        with tsv.open(newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f, delimiter='\t'):
                if row['level'] != '5' or not row['text'].strip():
                    continue
                tokens.append({'text': row['text'], 'confidence': float(row['conf']) / 100,
                               'box': [int(row[k]) for k in ('left', 'top', 'width', 'height')],
                               'lineId': '-'.join(row[k] for k in ('page_num', 'block_num', 'par_num', 'line_num'))})
                if len(tokens) > 4096:
                    raise ValueError('Too many OCR tokens')
        return tokens


def image_proposal(data, context, *, extractor=local_tesseract, ledger=(), recheck=None):
    """Untrusted extraction only. Exact-byte image dedup; no receipt identity guessed."""
    context = _capture(context)
    _gate(context)
    if not callable(recheck):
        raise ValueError('Authoritative admission recheck required')
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_BYTES:
        raise ValueError('Expected bounded image bytes')
    from PIL import Image
    with Image.open(io.BytesIO(data)) as image:
        if image.format not in ('PNG', 'JPEG') or image.width * image.height > MAX_PIXELS or getattr(image, 'n_frames', 1) != 1:
            raise ValueError('Unsupported or oversized image')
        image.load()
        width, height = image.size
        digest = hashlib.sha256(data).hexdigest()
        if len(ledger) > 10000:
            raise ValueError('Ledger bound exceeded')
        if any(x.get('accountId') == context['accountId'] and x.get('sourceId') == context['sourceId'] and x.get('imageDigest') == digest for x in ledger):
            _recheck(context, recheck)
            return {'status': 'duplicate-image', 'imageDigest': digest}
        raw = extractor(image)
    if not isinstance(raw, list) or not 1 <= len(raw) <= 4096:
        raise ValueError('Expected bounded OCR tokens')
    tokens, lines = [], {}
    for token in raw:
        text, line_id = _text(token['text']), _text(token['lineId'])
        box, confidence = token['box'], token['confidence']
        if not isinstance(box, list) or len(box) != 4 or any(type(v) is not int or v < 0 for v in box) or box[0]+box[2] > width or box[1]+box[3] > height:
            raise ValueError('Invalid OCR coordinates')
        if type(confidence) not in (int, float) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError('Invalid OCR confidence')
        clean = {'text': text, 'lineId': line_id, 'box': list(box), 'confidence': confidence}
        tokens.append(clean)
        lines.setdefault(line_id, []).append(clean)
    if len(lines) > 200:
        raise ValueError('Too many receipt lines')
    ocr_lines = []
    for line_id, words in lines.items():
        words.sort(key=lambda x: (x['box'][0], x['box'][1]))
        original = ' '.join(w['text'] for w in words)
        if len(original) > 2000:
            raise ValueError('OCR line too long')
        ocr_lines.append({'id': line_id, 'originalText': original, 'name': None,
                          'quantity': None, 'unit': None, 'confidence': min(w['confidence'] for w in words)})
    # Ready for actual JS prepareReceipt(input, context); tokens remain separate evidence.
    helper_input = {'accountId': context['accountId'], 'sourceId': context['sourceId'],
                    'contentDigest': digest, 'retainUntil': context['retainUntil'],
                    'image': None, 'ocr': {'lines': ocr_lines}}
    _recheck(context, recheck)
    return {'status': 'needs-review', 'imageDigest': digest, 'tokens': tokens,
            'helperInput': helper_input, 'price': None, 'receiptId': None,
            'deleteTransientImage': True, 'uncertainty': 'OCR confidence is not correctness; fields require explicit review'}


def review_proposal(proposal, context, *, receipt_id, confirmed, reviews, ledger=()):
    """User decisions, never stock admission. Call under owning account transaction."""
    _gate(context)
    _text(receipt_id)
    if proposal.get('status') != 'needs-review' or confirmed is not True:
        raise ValueError('Explicit user review required')
    helper = proposal['helperInput']
    if helper['accountId'] != context['accountId'] or helper['sourceId'] != context['sourceId'] or helper['retainUntil'] <= context['now'] or helper['retainUntil'] > context['retainUntil'] or helper['contentDigest'] != proposal['imageDigest']:
        raise ValueError('Proposal scope or retention mismatch')
    lines = helper['ocr']['lines']
    if not isinstance(reviews, list) or len(reviews) != len(lines):
        raise ValueError('Review every line')
    by_id = {r['id']: r for r in reviews}
    if len(by_id) != len(reviews) or set(by_id) != {x['id'] for x in lines}:
        raise ValueError('Review source identities exactly once')
    clean, field_review = [], []
    for line in lines:
        r = by_id[line['id']]
        if r.get('decision') not in ('include', 'exclude'):
            raise ValueError('Explicit decision required')
        out = {'id': line['id'], 'decision': r['decision']}
        if r['decision'] == 'include':
            name, amount, unit = r.get('name'), r.get('quantity'), r.get('unit')
            if name is not None: _text(name)
            if amount is not None and (type(amount) not in (int, float) or not math.isfinite(amount) or amount <= 0):
                raise ValueError('Invalid reviewed quantity')
            if unit is not None: _text(unit)
            out.update(name=name, quantity=amount, unit=unit)
        price, purchase_date = None, None
        if r['decision'] == 'include':
            price = r.get('price')
            if price is not None:
                if not isinstance(price, dict) or set(price) != {'amount', 'currency', 'basis'} or not isinstance(price['amount'], str) or not re.fullmatch(r'\d{1,12}(?:\.\d{1,4})?', price['amount']) or not isinstance(price['currency'], str) or not re.fullmatch('[A-Z]{3}', price['currency']):
                    raise ValueError('Explicit price amount/currency/basis required')
                _text(price['basis'])
                price = dict(price)
            purchase_date = r.get('purchaseDate')
            if purchase_date is not None:
                if not isinstance(purchase_date, str) or date.fromisoformat(purchase_date).isoformat() != purchase_date:
                    raise ValueError('Invalid reviewed purchase date')
        field_review.append({**out, 'price': price, 'purchaseDate': purchase_date})
        clean.append(out)
    if len(ledger) > 10000: raise ValueError('Ledger bound exceeded')
    duplicate = any(x.get('accountId') == context['accountId'] and x.get('sourceId') == context['sourceId'] and
                    (x.get('receiptId') == receipt_id or x.get('imageDigest') == proposal['imageDigest']) for x in ledger)
    return {'status': 'duplicate' if duplicate else 'reviewed-proposal',
            'helperReview': {'confirmed': True, 'lines': clean}, 'reviewedFields': field_review,
            'ledgerEntry': None if duplicate else {'accountId': context['accountId'], 'sourceId': context['sourceId'],
            'receiptId': receipt_id, 'imageDigest': proposal['imageDigest'], 'retainUntil': helper['retainUntil']},
            'inventoryAuthority': False}


def retention_plan(context, *, withdrawn=False, image_retained=False, image_until=None):
    """Instruction only; caller owns deletion/backup/consent lifecycle, never arbitrary paths."""
    now = context['now']
    if type(now) is not int or now < 0: raise ValueError('Invalid clock')
    _text(context['accountId'])
    if type(context['retainUntil']) is not int: raise ValueError('Invalid retention deadline')
    try:
        _gate(context)
        admitted = True
    except ValueError:
        admitted = False
    delete = withdrawn is True or now >= context['retainUntil'] or not admitted
    keep_image = (not delete and context.get('consent', {}).get('accountId') == context['accountId'] and
                  context.get('consent', {}).get('retainImage') is True and
                  type(image_until) is int and now < image_until <= context['retainUntil'])
    return {'deleteImage': bool(image_retained and not keep_image), 'deleteTokens': delete,
            'deleteProposal': delete, 'deleteLedger': delete, 'originalRetentionPermitted': keep_image}

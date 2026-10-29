// Pure private receipt review. No provider, persistence, inventory or UI side effects.
const text = (value, label, max = 200) => {
  if (typeof value !== 'string' || !value.trim() || value.length > max) throw Error(`Invalid ${label}`);
  return value;
};
const time = value => {
  if (!Number.isSafeInteger(value) || value < 0) throw Error('Invalid clock or retention deadline');
  return value;
};
const optionalText = value => value == null ? null : text(value, 'field');
const quantity = value => {
  if (value == null) return null;
  if (!Number.isFinite(value) || value <= 0) throw Error('Invalid quantity');
  return value;
};
const fields = value => ({name: optionalText(value.name), quantity: quantity(value.quantity), unit: optionalText(value.unit)});
const key = value => JSON.stringify([value.accountId, value.sourceId, value.contentDigest]);
function gate(receipt, {accountId, now, consent, rights}) {
  time(now);
  if (receipt.accountId !== accountId) throw Error('Account scope mismatch');
  if (now >= receipt.retainUntil) throw Error('Receipt retention expired');
  if (consent?.accountId !== accountId || consent.receiptReview !== true || time(consent.expiresAt) <= now)
    throw Error('Current receipt review consent required');
  if (rights?.sourceId !== receipt.sourceId || rights.privateUse !== true || time(rights.expiresAt) <= now)
    throw Error('Current private source rights required');
}

// contentDigest must identify exact source bytes, computed by the owning adapter.
export function prepareReceipt({accountId, sourceId, contentDigest, ocr, retainUntil, image = null}, context) {
  const draft = {
    accountId: text(accountId, 'account'), sourceId: text(sourceId, 'source'),
    contentDigest: text(contentDigest, 'content digest'), retainUntil: time(retainUntil),
    createdAt: time(context.now), status: 'needs-review',
  };
  gate(draft, context);
  if (!Array.isArray(ocr?.lines) || !ocr.lines.length || ocr.lines.length > 200) throw Error('Expected 1–200 OCR lines');
  const ids = new Set();
  draft.lines = ocr.lines.map(line => {
    const id = text(line.id, 'source line ID');
    if (ids.has(id)) throw Error('Duplicate source line ID');
    ids.add(id);
    const confidence = line.confidence ?? null;
    if (confidence !== null && (!Number.isFinite(confidence) || confidence < 0 || confidence > 1)) throw Error('Invalid OCR confidence');
    return {id, originalText: text(line.originalText, 'source text', 2000), extracted: fields(line), confidence};
  });
  // No pixels, image URL, medical, ingredient or purchase-authority fields are copied.
  draft.image = image === null ? null : {
    id: text(image.id, 'image ID'), retainUntil: time(image.retainUntil),
  };
  if (draft.image && (draft.image.retainUntil <= context.now || draft.image.retainUntil > draft.retainUntil || context.consent.retainImage !== true))
    throw Error('Explicit image consent and bounded retention required');
  return draft;
}

// Ledger is supplied from the active account's authoritative store. The owning
// adapter must atomically check + persist this result to protect concurrent calls.
export function reviewReceipt(draft, {confirmed, lines}, ledger, context) {
  gate(draft, context);
  if (draft.status !== 'needs-review' || confirmed !== true) throw Error('Explicit receipt review required');
  if (!Array.isArray(ledger) || ledger.length > 10000) throw Error('Invalid receipt ledger');
  if (!Array.isArray(lines) || lines.length !== draft.lines.length) throw Error('Review every source line');
  const byId = new Map(lines.map(line => [line.id, line]));
  if (byId.size !== lines.length) throw Error('Duplicate reviewed line ID');
  const reviewed = draft.lines.map(line => {
    const review = byId.get(line.id);
    if (!review || !['include', 'exclude'].includes(review.decision)) throw Error('Explicit decision for every source line required');
    return {...line, extracted: {...line.extracted}, decision: review.decision,
      reviewed: review.decision === 'exclude' ? null : fields(review)};
  });
  const duplicate = ledger.some(entry => key(entry) === key(draft));
  if (duplicate) return {status: 'duplicate', receipt: null, ledgerEntry: null};
  const retention = receiptRetentionPlan(draft, {...context, retainImage: context.consent.retainImage === true});
  return {status: 'reviewed', retention, receipt: {...draft, image: retention.deleteImage ? null : draft.image && {...draft.image}, lines: reviewed,
    status: 'reviewed', reviewedAt: context.now, rights: {privateUse: true, sharedPublication: false, expiresAt: context.rights.expiresAt},
    consentExpiresAt: context.consent.expiresAt,
  }, ledgerEntry: {accountId: draft.accountId, sourceId: draft.sourceId, contentDigest: draft.contentDigest, retainUntil: draft.retainUntil}};
}

// This is an instruction plan, never a claim that deletion has happened.
// Withdrawal removes the receipt and image; the adapter also removes its ledger.
export function receiptRetentionPlan(receipt, {accountId, now, withdrawn = false, retainImage = false}) {
  time(now);
  if (accountId !== receipt.accountId) throw Error('Account scope mismatch');
  const deleteReceipt = withdrawn || now >= receipt.retainUntil;
  return {deleteReceipt, deleteLedger: deleteReceipt,
    deleteImage: !!receipt.image && (deleteReceipt || !retainImage || now >= receipt.image.retainUntil)};
}

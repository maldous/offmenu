// Pure cost estimates for caller-selected, explicitly matched offers. No acquisition or purchase.
const text = value => typeof value === 'string' && value.trim().length > 0 && value.length <= 300;
const amount = value => Number.isSafeInteger(value) && value >= 0;
const quantity = value => typeof value === 'number' && Number.isFinite(value) && value > 0;
const units = new Map([['g', ['mass', 1]], ['kg', ['mass', 1000]], ['ml', ['volume', 1]], ['l', ['volume', 1000]], ['count', ['count', 1]]]);
const day = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && Number.isFinite(Date.parse(value + 'T00:00:00Z')) && new Date(value + 'T00:00:00Z').toISOString().slice(0, 10) === value;
const currencyCode = value => typeof value === 'string' && /^[A-Z]{3}$/.test(value);
const safeSum = values => { const sum = values.reduce((a, b) => a + b, 0); return amount(sum) ? sum : null; };

function estimateLine({ need = {}, offer = {} }, context) {
  const reasons = [];
  const reject = (condition, reason) => { if (condition) reasons.push(reason); };
  reject(!text(need.productId) || need.productId !== offer.productId, 'product-mismatch');
  reject(!text(offer.id) || !text(offer.storeId), 'identity-missing');
  reject(offer.accountId !== context.accountId, 'account-mismatch');
  reject(offer.currency !== context.currency, 'currency-mismatch');
  const p = offer.provenance;
  reject(!p || !text(p.sourceId) || !text(p.recordId) || !text(p.license) || !text(p.rights) || !['private', 'public'].includes(p.visibility), 'provenance-missing');
  const windowSupplied = offer.validFrom != null || offer.validThrough != null;
  const windowValid = day(offer.validFrom) && day(offer.validThrough) && offer.validFrom <= offer.validThrough && offer.validFrom <= context.date && context.date <= offer.validThrough;
  reject(!day(offer.observedOn) || offer.observedOn > context.date || (windowSupplied ? !windowValid : offer.observedOn !== context.date), 'date-incompatible');
  reject(!quantity(need.quantity) || !quantity(offer.pack?.quantity), 'quantity-unknown');
  const needUnit = units.get(need.unit), packUnit = units.get(offer.pack?.unit);
  reject(!needUnit || !packUnit || needUnit[0] !== packUnit[0], 'unit-incompatible');
  reject(!amount(offer.priceMinor), 'price-unknown');
  let packs = null, acquiredQuantity = null, leftoverQuantity = null, purchaseCostMinor = null, consumedCostMinor = null, unitPriceMinor = null;
  if (!reasons.length) {
    const packInNeedUnit = offer.pack.quantity * packUnit[1] / needUnit[1];
    packs = Math.ceil(need.quantity / packInNeedUnit);
    acquiredQuantity = packs * packInNeedUnit;
    purchaseCostMinor = packs * offer.priceMinor;
    consumedCostMinor = need.quantity / packInNeedUnit * offer.priceMinor;
    unitPriceMinor = offer.priceMinor / packInNeedUnit;
    leftoverQuantity = acquiredQuantity - need.quantity;
    if (!quantity(packInNeedUnit) || !Number.isSafeInteger(packs) || packs < 1 || !amount(purchaseCostMinor) || ![acquiredQuantity, consumedCostMinor, unitPriceMinor, leftoverQuantity].every(Number.isFinite) || acquiredQuantity > Number.MAX_SAFE_INTEGER || leftoverQuantity < 0) {
      reasons.push('arithmetic-out-of-bounds');
      packs = acquiredQuantity = leftoverQuantity = purchaseCostMinor = consumedCostMinor = unitPriceMinor = null;
    }
  }
  return { needId: need.id, productId: need.productId ?? null, offerId: offer.id ?? null, storeId: offer.storeId ?? null, accountId: offer.accountId ?? null, currency: offer.currency ?? null, observedOn: offer.observedOn ?? null, validFrom: offer.validFrom ?? null, validThrough: offer.validThrough ?? null, provenance: p ? structuredClone(p) : null, uncertainty: structuredClone(offer.uncertainty ?? null), requestedQuantity: need.quantity ?? null, unit: need.unit ?? null, pack: structuredClone(offer.pack ?? null), packs, acquiredQuantity, leftoverQuantity, purchaseCostMinor, consumedCostMinor, unitPriceMinor, reasons };
}

/**
 * Evaluate 1–100 selected need/offer pairs, at an explicit caller date and account.
 * Prices and fees are integer minor currency units; budget uses the same units.
 * Fees must be complete per-store totals (including tax/delivery/service as applicable).
 * Unknown input withholds total/budget conclusions; knownSubtotalMinor is only partial.
 */
export function evaluateOfferBasket({ accountId, date, currency, lines, fees = [], maxStoreStops = null, budgetMinor = null }) {
  if (!text(accountId) || !day(date) || !currencyCode(currency)) throw new Error('Explicit account, calendar date and currency required');
  if (!Array.isArray(lines) || !lines.length || lines.length > 100 || !Array.isArray(fees) || fees.length > 100) throw new Error('Provide 1–100 selected lines and at most 100 store fees');
  const needs = new Set(), feeMap = new Map();
  for (const line of lines) {
    if (!line || !text(line.need?.id) || needs.has(line.need.id)) throw new Error('Unique need ids required; aggregate the same need before quoting');
    needs.add(line.need.id);
  }
  for (const fee of fees) {
    if (!fee || !text(fee.storeId) || feeMap.has(fee.storeId)) throw new Error('Unique store fee ids required');
    feeMap.set(fee.storeId, fee);
  }
  const results = lines.map(line => estimateLine(line, { accountId, date, currency }));
  const stores = [...new Set(results.map(line => line.storeId).filter(text))];
  const feeResults = stores.map(storeId => {
    const fee = feeMap.get(storeId);
    const known = fee?.date === date && fee?.currency === currency && amount(fee?.amountMinor);
    return { storeId, date: fee?.date ?? null, currency: fee?.currency ?? null, amountMinor: known ? fee.amountMinor : null, reason: known ? null : 'fee-unknown-or-incompatible' };
  });
  const knownSubtotalMinor = safeSum([...results.map(r => r.purchaseCostMinor), ...feeResults.map(f => f.amountMinor)].filter(v => v !== null));
  const complete = results.every(r => !r.reasons.length) && feeResults.every(f => f.amountMinor !== null) && knownSubtotalMinor !== null;
  const totalMinor = complete ? knownSubtotalMinor : null;
  const budgetStatus = totalMinor === null || !amount(budgetMinor) ? 'unknown' : totalMinor <= budgetMinor ? 'within' : 'exceeded';
  const storeStopStatus = results.some(r => !text(r.storeId)) || !amount(maxStoreStops) ? 'unknown' : stores.length <= maxStoreStops ? 'within' : 'exceeded';
  const withinBounds = budgetStatus === 'exceeded' || storeStopStatus === 'exceeded' ? false : budgetStatus === 'within' && storeStopStatus === 'within' ? true : null;
  return { calculationVersion: 'offer-cost/1', status: complete ? 'cost-estimate' : 'withheld', accountId, date, currency, lines: results, fees: feeResults, storeStops: stores.length, storeStopStatus, knownSubtotalMinor, totalMinor, budgetMinor: amount(budgetMinor) ? budgetMinor : null, budgetStatus, withinBounds, notice: 'Dated cost estimate only. Availability, suitability, rights, consent and purchase authority require separate review.' };
}

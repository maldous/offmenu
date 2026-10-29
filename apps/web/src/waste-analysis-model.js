// Read-only analysis of owner-adapted, consented, account-scoped snapshots.
// No stock deduction, conversion, clock, persistence, transport or purchase action.
const positive = value => Number.isFinite(value) && value > 0;
const finiteSum = (left, right) => {
  const sum = left + right;
  if (!Number.isFinite(sum)) throw new RangeError('Waste aggregate overflow');
  return sum;
};
const text = value => typeof value === 'string' && value.trim().length > 0;

export function analyzeWaste(input, { accountId } = {}) {
  if (!text(accountId)) throw new TypeError('Explicit account required');
  if (!Array.isArray(input) || input.length > 1000) throw new TypeError('At most 1000 waste records required');
  const quantities = new Map(), values = new Map(), suggestions = [];
  let unknownQuantityRecords = 0, unknownValueRecords = 0;
  const records = input.map(row => {
    if (!row || row.accountId !== accountId) throw new TypeError('Waste account mismatch');
    if (!text(row.sourceId) || !text(row.receiptId)) throw new TypeError('Source and receipt identities required');
    const quantity = row.measured === true && positive(row.quantity) && text(row.unit) ? row.quantity : null;
    const cost = row.costSnapshot;
    let value = null;
    if (quantity !== null && cost?.sourceId === row.sourceId && cost.unit === row.unit &&
        positive(cost.quantity) && quantity <= cost.quantity && Number.isFinite(cost.amount) &&
        cost.amount >= 0 && text(cost.currency)) {
      const amount = cost.amount * (quantity / cost.quantity);
      if (Number.isFinite(amount)) value = { amount, currency: cost.currency };
    }
    if (quantity === null) unknownQuantityRecords++;
    else quantities.set(row.unit, finiteSum(quantities.get(row.unit) || 0, quantity));
    if (!value) unknownValueRecords++;
    else {
      const total = values.get(value.currency) || { currency:value.currency, amount:0, knownRecords:0 };
      total.amount = finiteSum(total.amount, value.amount); total.knownRecords++;
      values.set(value.currency, total);
    }
    // Only a recorded oversized-pack reason supports this optional planning prompt.
    // Season is caller-supplied observation, never inferred from a date or country.
    if (quantity !== null && row.reason === 'oversized-pack' && text(row.season) &&
        cost?.sourceId === row.sourceId && cost.unit === row.unit && positive(cost.quantity) && quantity <= cost.quantity) {
      if (row.packOptions != null && (!Array.isArray(row.packOptions) || row.packOptions.length > 100))
        throw new TypeError('At most 100 pack options required');
      const packSourceIds = [...new Set((row.packOptions || []).filter(pack =>
        pack && text(pack.sourceId) && pack.unit === row.unit && pack.season === row.season &&
        positive(pack.quantity) && pack.quantity < cost.quantity).map(pack => pack.sourceId))];
      if (packSourceIds.length) suggestions.push({receiptId:row.receiptId, sourceId:row.sourceId,
        reason:row.reason, season:row.season, kind:'consider-smaller-pack', packSourceIds});
    }
    return {accountId,receiptId:row.receiptId,sourceId:row.sourceId,quantity,
      unit:text(row.unit)?row.unit:null,reason:text(row.reason)?row.reason:null,
      season:text(row.season)?row.season:null,value};
  });
  return {records,quantities:[...quantities].map(([unit,quantity])=>({unit,quantity})),
    values:[...values.values()],coverage:{records:records.length,unknownQuantityRecords,unknownValueRecords},suggestions};
}

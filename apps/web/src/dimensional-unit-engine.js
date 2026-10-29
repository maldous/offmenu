/**
 * Isolated common-data quantity conversion; integration requires Morgan review.
 * Accepts corpus/common-data.schema.json quantity objects and canonical unit IDs.
 * Only registered SI mass/volume scale changes are supported. No lexical parsing,
 * density, item mass, yield, ingredient equivalence, or preparation/basis changes.
 * Source evidence stays verbatim in both source and the derived quantity. This
 * establishes unit arithmetic, never food identity or planning qualification.
 * Unknown/qualified values and custom definitions require separate review.
 */
const prefix = 'urn:offmenu:unit:';
const units = new Map([
  ['g', 'mass', 0], ['kg', 'mass', 3], ['mg', 'mass', -3],
  ['microgram', 'mass', -6], ['ml', 'volume', 0], ['l', 'volume', 3],
].map(([id, dimension, exponent]) => [prefix + id, {dimension, exponent}]));
const magnitude = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;

/** Returns {status, reason?, source, quantity, derivation?}; never mutates input.
 * Unresolved results have quantity:null, retaining the entire original in source.
 * Range endpoints scale independently; null/open bounds stay null. Qualifiers
 * are conservatively withheld because they can denote limits or unreliable data.
 * Denominators and preparation metadata are preserved, never rescaled implicitly.
 */
export function convertQuantity(input, targetUnitId) {
  const source = structuredClone(input);
  const unresolved = reason => ({status: 'unresolved', reason, source, quantity: null});
  if (!source || source.kind !== 'quantity' || !Array.isArray(source.qualifiers)) {
    return unresolved('invalid-quantity');
  }
  const from = units.get(source.unitId), to = units.get(targetUnitId);
  if (!from || !to) return unresolved('unsupported-unit');
  if (source.dimension !== from.dimension) return unresolved('unit-dimension-mismatch');
  if (from.dimension !== to.dimension) return unresolved('incompatible-dimensions');
  if (source.definitionId != null) return unresolved('custom-definition-requires-review');
  if (source.qualifiers.length) return unresolved('qualified-quantity-requires-review');
  if (source.value !== null && !magnitude(source.value)) return unresolved('invalid-value');
  const range = source.range;
  if (range !== undefined && (!range ||
      ![range.min, range.max].every(x => x === null || magnitude(x)) ||
      range.min !== null && range.max !== null && range.min > range.max ||
      source.value !== null && (range.min !== null && source.value < range.min ||
        range.max !== null && source.value > range.max))) return unresolved('invalid-range');
  if (source.value === null && (!range || range.min === null && range.max === null)) {
    return unresolved('unknown-value');
  }
  // Integer exponent differences avoid dividing rounded binary scale constants.
  // Derived values still use JavaScript Number precision; originals stay exact.
  const factor = 10 ** (from.exponent - to.exponent);
  const scale = x => x === null ? null : x * factor;
  const value = scale(source.value);
  const convertedRange = range && {min: scale(range.min), max: scale(range.max)};
  const outputs = [value, ...(convertedRange ? [convertedRange.min, convertedRange.max] : [])];
  if (outputs.some(x => x !== null && !magnitude(x))) return unresolved('numeric-overflow');
  const inputs = [source.value, ...(range ? [range.min, range.max] : [])];
  if (outputs.some((x, i) => x === 0 && inputs[i] > 0)) return unresolved('numeric-underflow');
  return {
    status: 'converted', source,
    quantity: {...structuredClone(source), value, unitId: targetUnitId,
      ...(convertedRange ? {range: convertedRange} : {})},
    derivation: {method: 'defined-unit-scale/1', fromUnitId: source.unitId, targetUnitId, factor},
  };
}

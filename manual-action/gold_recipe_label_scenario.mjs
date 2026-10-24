/** Pure projection of explicitly supplied, already-qualified source labels.
 * Caller owns snapshot admission, source-use permission and evidence selection.
 * This module cannot establish actual recipe/product equivalence or cooked yield.
 */
import {calculateBasket, CALCULATION_VERSION} from '../public/basket-model.js';

export const SCENARIO_VERSION = 'offmenu.source-label-input-scenario/1';
const sha = x => typeof x === 'string' && /^[a-f0-9]{64}$/.test(x);
const text = x => typeof x === 'string' && !!x.trim();
const number = x => typeof x === 'number' && Number.isFinite(x) && x >= 0 && x <= 1e6;
const requireInput = (ok, reason) => { if (!ok) throw new Error(reason); };
const canonical = x => JSON.stringify(x, (_, v) => v && !Array.isArray(v) && typeof v === 'object'
  ? Object.fromEntries(Object.keys(v).sort().map(k => [k, v[k]])) : v);
const same = (a, b) => canonical(a) === canonical(b);

function bounded(value, bytes = 524288) {
  let nodes = 0;
  const ancestors = new Set();
  function visit(x, depth) {
    requireInput(++nodes <= 20000 && depth <= 20, 'input-structure-limit');
    if (x && typeof x === 'object') {
      requireInput(!ancestors.has(x) && (Array.isArray(x) || Object.getPrototypeOf(x) === Object.prototype), 'json-required');
      ancestors.add(x);
      for (const v of Object.values(x)) visit(v, depth + 1);
      ancestors.delete(x);
    } else requireInput(x === null || typeof x === 'string' || typeof x === 'boolean'
      || typeof x === 'number' && Number.isFinite(x), 'finite-json-required');
  }
  visit(value, 0);
  requireInput(new TextEncoder().encode(JSON.stringify(value)).length <= bytes, 'input-byte-limit');
}

function cited(ids, citations) {
  return Array.isArray(ids) && ids.length > 0 && ids.length <= 64
    && new Set(ids).size === ids.length && ids.every(id => text(id)
      && citations[id]?.id === id && text(citations[id]?.license) && text(citations[id]?.attribution));
}

function supported(records, kind, target, scope, ids) {
  return Array.isArray(records) && ids.every(cid => records.some(s => s.target_kind === kind
    && s.target_id === target && s.support_scope === scope && s.citation_id === cid && sha(s.evidence_sha256)));
}

function nativeJSON(raw) {
  if (typeof raw !== 'string') return null;
  try {
    const value = JSON.parse(raw);
    bounded(value, 65536);
    return value;
  } catch { return null; }
}

function nativeSpans(value) {
  return Array.isArray(value) && value.length > 0 && value.length <= 64
    && value.every(s => s && typeof s === 'object' && Object.keys(s).length === 5
      && typeof s.pointer === 'string' && /^\/steps\/(0|[1-9][0-9]*)\/raw_text$/.test(s.pointer)
      && Number.isSafeInteger(s.start) && Number.isSafeInteger(s.end)
      && 0 <= s.start && s.start < s.end && s.end <= 1e6
      && s.offset_unit === 'unicode_codepoint' && text(s.text)
      && Array.from(s.text).length === s.end - s.start);
}

function nativeIngredientBound(line, input) {
  const q = line.quantityEvidence, record = q?.ingredientRecord, supports = q?.ingredientSupport;
  const evidence = nativeJSON(record?.evidence_json);
  if (!(record && sha(line.ingredientEntityId) && text(q?.slotName)
    && record.run_id === input.recipe.runId && record.run_id === q.runId
    && record.action_id === q.actionId && record.slot_name === q.slotName
    && record.source_ingredient_line_id === line.ingredientId && record.source_ingredient_line_id === q.ingredientId
    && record.ingredient_entity_id === line.ingredientEntityId
    && same(nativeJSON(record.allocation_json), q.allocation) && nativeSpans(evidence)
    && cited(q.citationIds, input.citations) && Array.isArray(supports)
    && supports.length === q.citationIds.length
    && new Set(supports.map(s => s?.citation_id)).size === supports.length)) return false;
  return supports.every(s => s?.run_id === record.run_id && s.action_id === record.action_id
    && s.slot_name === record.slot_name && q.citationIds.includes(s.citation_id)
    && same(nativeJSON(s.evidence_json), evidence));
}

function lineReasons(line, input) {
  const q = line.quantityEvidence, a = q?.allocation, p = line.product, s = line.selection;
  const reasons = [];
  if (!(number(line.massG) && line.massG > 0 && line.massUnit === 'g'
    && q?.runId === input.recipe.runId && q?.ingredientId === line.ingredientId
    && text(q?.actionId) && a?.original?.unit === 'g' && Number(a.original.value) === line.massG
    && a?.factor === '1' && a?.normalized_unit === 'g' && a?.normalized?.exact === true
    && a?.normalized?.status === 'normalized' && a?.normalized?.unit === 'g'
    && a?.normalized?.dimension === 'mass' && same(a.normalized.original, a.original)
    && Array.isArray(a.normalized.issues) && a.normalized.issues.length === 0
    && Number(a.normalized.value) === line.massG && Number(a.scaled_min) === line.massG
    && Number(a.scaled_max) === line.massG && cited(q?.citationIds, input.citations))) {
    reasons.push('exact-once-gram-allocation-unqualified');
  }
  if (!nativeIngredientBound(line, input)) reasons.push('native-ingredient-record-or-support-unqualified');
  if (!(s?.origin === 'GENERATED' && text(s.productId) && s.productId === p?.id
    && text(s.variantAssumption) && text(s.massStateAssumption))) reasons.push('explicit-generated-product-selection-required');
  if (!(p?.domain === 'barcodes' && p?.type === 'barcode-product' && p?.state === 'verified'
    && sha(p.entityId) && text(p.id) && p.scope?.visibility === 'public'
    && cited(p.citationIds, input.citations))) reasons.push('qualified-source-product-label-required');
  return reasons;
}

function observationReasons(o, line, metric, input) {
  const v = o.original, c = o.claim, ctx = o.context, basis = v?.basis;
  const reasons = [];
  const units = {G: 'g', MG: 'mg', UG: 'µg', KCAL: 'kcal', KJ: 'kJ'};
  if (!(o.state === 'verified' && o.entityId === line.product?.entityId && o.metricId === metric.id
    && text(o.id) && c?.subjectId === line.product?.id && c?.propertyId === metric.id
    && same(c.value, v) && c.scope?.visibility === 'public')) reasons.push('observation-product-binding-unqualified');
  if (!(v?.kind === 'quantity' && number(v.value) && text(v.sourceValue)
    && Number(v.sourceValue) === v.value && units[v.sourceUnit] === v.unitId
    && v.unitId === metric.unit && v.dimension === metric.dimension
    && basis?.dimension === 'mass' && basis?.unitId === 'g' && basis?.value === 100
    && same(basis, ctx?.basis))) reasons.push('native-value-unit-or-mass-basis-unqualified');
  const methods = {LCCS: 'Calculated from value per serving size measure',
    LCCD: 'Calculated from a daily value percentage per serving size measure'};
  if (!(Object.hasOwn(methods, ctx?.sourceDerivationCode ?? '')
    && ctx.method === methods[ctx.sourceDerivationCode] && text(ctx.uncertainty)
    && ctx.underlyingIndependentMeasurementCount === 0)) reasons.push('source-label-method-unqualified');
  if (!(cited(c?.citationIds, input.citations)
    && supported(o.supportRecords, 'assertion', c?.id, 'field', c?.citationIds ?? []))) reasons.push('observation-rights-or-support-unqualified');
  if (!(metric.state === 'verified' && cited(metric.citationIds, input.citations)
    && supported(metric.supportRecords, 'metric', metric.id, 'definition', metric.citationIds ?? []))) {
    reasons.push('nutrient-definition-rights-or-support-unqualified');
  }
  return reasons;
}

export function evaluateLabelScenario(input, selectedSnapshot) {
  bounded(input); bounded(selectedSnapshot);
  input = JSON.parse(JSON.stringify(input));
  requireInput(input?.schemaVersion === SCENARIO_VERSION && text(input.id), 'scenario-schema-required');
  requireInput(sha(selectedSnapshot?.databaseSha256) && sha(selectedSnapshot?.admissionSha256)
    && same(input.snapshot, selectedSnapshot), 'independently-selected-snapshot-required');
  requireInput(['GENERATED_SOURCE_LABEL_SCENARIO', 'ACTUAL_RECIPE_COMPOSITION'].includes(input.mode), 'scenario-mode-required');
  requireInput(typeof input.recipe?.runId === 'string' && /^recipe-actions:[a-f0-9]{64}$/.test(input.recipe.runId)
    && input.recipe?.repeatCount === 1
    && Array.isArray(input.recipe.ingredientIds) && input.recipe.ingredientIds.length > 0
    && input.recipe.ingredientIds.every(text), 'once-only-recipe-input-required');
  requireInput(Array.isArray(input.lines) && input.lines.length > 0 && input.lines.length <= 8
    && Array.isArray(input.metrics) && input.metrics.length > 0 && input.metrics.length <= 64
    && input.citations && Object.keys(input.citations).length <= 256, 'scenario-count-limit');
  const ids = input.lines.map(l => l.ingredientId), mids = input.metrics.map(m => m.id);
  requireInput(ids.every(text) && new Set(ids).size === ids.length
    && new Set(input.recipe.ingredientIds).size === input.recipe.ingredientIds.length
    && same([...ids].sort(), [...input.recipe.ingredientIds].sort()), 'exact-once-complete-ingredient-set-required');
  requireInput(mids.every(id => typeof id === 'string' && /^[a-z][a-z0-9.-]*:[A-Za-z0-9:._-]{1,180}$/.test(id))
    && new Set(mids).size === mids.length && input.metrics.every(m => text(m.name) && text(m.unit)
      && ['mass', 'energy'].includes(m.dimension)), 'unique-nutrient-definitions-required');
  requireInput(input.lines.every(l => Array.isArray(l.observations) && l.observations.length <= 64), 'observation-count-limit');
  const globalReasons = input.mode === 'ACTUAL_RECIPE_COMPOSITION'
    ? ['actual-ingredient-variant-product-binding-not-established'] : [];
  const details = input.lines.map(line => ({ingredientId: line.ingredientId,
    reasons: [...globalReasons, ...lineReasons(line, input)]}));
  const basketLines = input.lines.map((line, i) => {
    const nutrients = {};
    for (const metric of input.metrics) {
      const observations = line.observations.filter(o => o.metricId === metric.id);
      const reasons = [...details[i].reasons];
      if (observations.length !== 1) reasons.push(observations.length ? 'ambiguous-observation-no-winner' : 'missing-source-observation');
      const observation = observations.length === 1 ? observations[0] : null;
      if (observation) reasons.push(...observationReasons(observation, line, metric, input));
      details[i][metric.id] = {holdReasons: reasons, observationId: observation?.id ?? null};
      if (!reasons.length) nutrients[metric.id] = {value: observation.original.value, unit: metric.unit,
        definition: metric.id, sourceId: line.product.id, basisAmount: 100, basisUnit: 'g',
        state: 'source-label-input', status: 'source-recorded-publisher-label'};
    }
    return {id: line.ingredientId, edibleG: number(line.massG) ? line.massG : null,
      state: 'source-label-input', nutrients};
  });
  const dictionary = input.metrics.map(m => ({metric_id: m.id, unit: m.unit}));
  const basket = lines => calculateBasket({id: input.id, track: 'generated-source-label-model',
    state: 'source-label-input', lines}, dictionary);
  const combined = basket(basketLines), individual = basketLines.map(l => basket([l]));
  const metrics = Object.fromEntries(input.metrics.map(metric => {
    const result = combined.metrics[metric.id];
    const contributions = individual.map((one, i) => ({ingredientId: input.lines[i].ingredientId,
      productId: input.lines[i].selection?.productId ?? null,
      ...details[i][metric.id], massG: input.lines[i].massG,
      sourceValue: input.lines[i].observations.find(o => o.id === details[i][metric.id].observationId)?.original ?? null,
      formula: 'source label value × ingredient input grams / 100 g',
      value: one.metrics[metric.id].total}));
    const known = contributions.some(c => c.value !== null);
    return [metric.id, {name: metric.name, unit: metric.unit,
      status: !known ? 'held-or-missing' : result.total === null ? 'partial' : 'conditional-input-sum',
      conditionalInputSum: result.total, knownSubtotal: known ? result.knownSubtotal : null,
      coverage: {qualifiedLines: contributions.filter(c => c.value !== null).length,
        requiredLines: input.lines.length, inputMassFraction: result.massCoverage}, contributions}];
  }));
  if (Object.values(metrics).every(m => m.knownSubtotal === null)) globalReasons.push('no-qualified-source-observations');
  const output = {schemaVersion: 'offmenu.source-label-input-scenario-result/1', id: input.id,
    mode: input.mode, state: globalReasons.length || details.some(d => d.reasons.length)
      ? 'HELD' : 'CONDITIONAL_SOURCE_LABEL_ARITHMETIC', holdReasons: [...new Set([...globalReasons, ...details.flatMap(d => d.reasons)])],
    calculatorVersion: CALCULATION_VERSION, metrics, inputs: input,
    actualRecipeNutrition: null, yieldG: null, servings: null, perServing: null, per100gPreparedFood: null,
    actualUserSelection: false, sourceReferenceNutritionTransfer: false, automaticPlanning: false,
    meaning: 'Explicit generated product-label input scenario only. Source labels, variants and preparation assumptions are not actual recipe composition, current analysis or dietary/safety qualification. Unknown nutrients are not zero; input mass is not output yield.'};
  bounded(output, 1048576);
  return output;
}

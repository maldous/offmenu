// Pure presentation adapter for basket/1.1. Callers retain admission/consent custody.
export const REFERENCE_VIEW_VERSION = 'reference-views/1';
export const COMPARISON_VIEWS = Object.freeze([
  'total', 'per100g', 'per1000kcal', 'equivalent2000kcal',
  'perPersonDay', 'perServing', 'percentReference',
]);
const finite = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
const positive = value => finite(value) && value > 0;
const named = value => typeof value === 'string' && value.trim().length > 0;

function servingFraction(result, serving) {
  if (!serving || !named(serving.sourceId) || !named(serving.recipeId) ||
      !named(serving.recipeVersion) || !named(result.basketId) ||
      serving.basketId !== result.basketId || serving.basketVersion !== result.version ||
      !named(result.state) || serving.state !== result.state) return null;
  // Exactly one declared method; an omitted serving is never a default portion.
  if (serving.fraction !== undefined && serving.massG === undefined) {
    return positive(serving.fraction) && serving.fraction <= 1 ? serving.fraction : null;
  }
  if (serving.massG !== undefined && serving.fraction === undefined) {
    return positive(serving.massG) && positive(result.massG) && serving.massG <= result.massG
      ? serving.massG / result.massG : null;
  }
  return null;
}

function referenceCompatible(result, metric, profile, reference) {
  return profile && ['system', 'id', 'name', 'version', 'lifeStage', 'sourceId'].every(key => named(profile[key])) &&
    profile.basis === 'person-day' && named(result.population) && result.population === profile.lifeStage &&
    reference?.status === 'complete' && positive(reference.value) && reference.unit === metric.unit &&
    Array.isArray(metric.definitions) && metric.definitions.length === 1 &&
    named(reference.definition) && metric.definitions[0] === reference.definition;
}

function view(value, unit, denominator, reason) {
  return {
    value: finite(value) ? value : null,
    unit,
    status: finite(value) ? 'available' : 'withheld',
    denominator,
    reason: finite(value) ? null : reason,
  };
}

/**
 * Adapt an existing calculateBasket result, without changing its arithmetic/lineage.
 * serving and referenceProfile must be admitted, owner-reviewed evidence. Metadata
 * is retained, not verified here. This does not authorize cross-profile comparisons.
 */
export function referenceViews(calculation, {serving = null, referenceProfile = null} = {}) {
  if (calculation?.calculationVersion !== 'basket/1.1' || !calculation.metrics ||
      Object.keys(calculation.metrics).length > 1000) throw new TypeError('Expected bounded basket/1.1 result');
  // Retain all custody metadata, including fields added by an authorised caller.
  const result = structuredClone(calculation);
  const basis = structuredClone({serving, referenceProfile});
  const fraction = servingFraction(result, basis.serving);
  const views = Object.fromEntries(Object.entries(result.metrics).map(([id, metric]) => {
    const complete = metric.status === 'complete' && finite(metric.total);
    const reference = basis.referenceProfile?.metrics?.[id];
    const compatible = referenceCompatible(result, metric, basis.referenceProfile, reference);
    const dayAmount = complete && positive(result.personDays) && finite(metric.perPersonDay)
      ? metric.perPersonDay : null;
    const existing = (key, amount, unit, scale = 1) => view(
      complete && positive(amount) ? metric[key] : null, metric.unit,
      {amount: amount ?? null, unit, scale}, 'Complete numerator and positive compatible denominator required',
    );
    return [id, {
      total: view(complete ? metric.total : null, metric.unit,
        {amount: 1, unit: 'basket'}, 'Complete numerator required'),
      per100g: existing('per100g', result.massG, 'g-edible', 100),
      per1000kcal: existing('per1000kcal', result.energyKcal, 'kcal', 1000),
      equivalent2000kcal: existing('equivalent2000kcal', result.energyKcal, 'kcal', 2000),
      perPersonDay: existing('perPersonDay', result.personDays, 'person-day'),
      perServing: view(complete && fraction !== null ? metric.total * fraction : null, metric.unit,
        {fraction, declared: basis.serving}, 'Version-bound serving mass or fraction required'),
      percentReference: view(dayAmount !== null && compatible ? 100 * dayAmount / reference.value : null, '%',
        {amount: reference?.value ?? null, unit: reference?.unit ?? null, basis: 'person-day',
          personDays: result.personDays ?? null, reference: reference ?? null},
        'Complete person-day amount and named compatible life-stage reference required'),
    }];
  }));
  return {
    viewVersion: REFERENCE_VIEW_VERSION,
    calculation: result,
    basis,
    referenceProfileKey: basis.referenceProfile
      ? ['system', 'id', 'version', 'lifeStage'].map(key => basis.referenceProfile[key] ?? null) : null,
    views,
    notice: 'Descriptive reference coverage only. No adequacy, deficiency, safety or overall health ranking. Admission and comparison gates remain with the caller.',
  };
}

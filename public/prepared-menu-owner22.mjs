// NORM-06 source-bound evidence projection. No cooking, scaling or admission.
export const PREPARED_MENU_VERSION = 'prepared-menu/1';
const named = x => typeof x === 'string' && x.trim().length > 0 && x.length <= 500;
const versioned = x => named(x) || (Number.isSafeInteger(x) && x >= 0);
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const clone = x => structuredClone(x);

function qualification(resolveScope, kind, binding, candidate, eligible) {
  if (!eligible) return {status:'unknown', scope:null, reason:'Source version, identity, form or basis unresolved', evidence:null};
  const verdict = resolveScope(clone({kind, binding, candidate}));
  if (verdict?.then) throw new TypeError('Scope resolver must be synchronous');
  const scope = kind === 'serving' ? 'portion-fraction' : 'culinary-function';
  const bound = verdict?.binding && Object.entries(binding).every(([key, value]) => equal(verdict.binding[key], value));
  const supported = verdict?.status === 'supported' && verdict.scope === scope && bound &&
    named(verdict.provenance?.sourceId) && named(verdict.provenance?.url);
  return {status:supported ? 'supported' : verdict?.status === 'conflict' ? 'conflict' : 'unknown',
    scope:supported ? scope : null, reason:supported ? null : 'No exact owner-qualified scope evidence',
    evidence:verdict ? clone(verdict) : null};
}

/** Owner must admit the source before calling. Resolver decisions are not sourced
 * from client status flags. Supported scope never certifies food/medical safety,
 * identity, nutrient equivalence, or redistribution. Production STOP remains. */
export function preparedMenuComposition(record, {serving = null, substitutions = [], resolveScope = () => null} = {}) {
  if (record?.kind !== 'recipe' || !named(record.id) || !Array.isArray(record.data?.ingredients) ||
      record.data.ingredients.length > 1000 || !Array.isArray(substitutions) || substitutions.length > 1000 ||
      typeof resolveScope !== 'function') throw new TypeError('Bounded source recipe and scope resolver required');
  const source = clone(record), data = source.data, recipeVersion = source.version ?? source.provenance?.revisionId ?? null;
  const requests = new Map();
  for (const proposal of clone(substitutions)) {
    if (!Number.isInteger(proposal.lineIndex) || proposal.lineIndex < 0 || proposal.lineIndex >= data.ingredients.length ||
        requests.has(proposal.lineIndex) || !named(proposal.replacement?.id)) {
      throw new TypeError('Unique source line index and replacement identity required');
    }
    requests.set(proposal.lineIndex, proposal);
  }
  const lines = data.ingredients.map((original, lineIndex) => {
    const parsedQuantity = {value:original.amount ?? null, unit:original.unit ?? null,
      basis:original.basis ?? null, form:original.form ?? original.state ?? null,
      status:original.quantityStatus ?? 'unknown'};
    const proposal = requests.get(lineIndex), replacement = proposal?.replacement;
    const binding = replacement ? {recipeId:source.id, recipeVersion, lineIndex,
      originalId:original.ingredientId ?? null, replacementId:replacement.id,
      replacementVersion:replacement.version ?? null, originalForm:parsedQuantity.form,
      replacementForm:replacement.form ?? null, originalBasis:parsedQuantity.basis,
      replacementBasis:replacement.basis ?? null, originalQuantity:clone(parsedQuantity),
      replacementQuantity:replacement.quantity ?? null} : null;
    const support = proposal ? qualification(resolveScope, 'substitution', binding, proposal,
      versioned(recipeVersion) && named(binding.originalId) && versioned(binding.replacementVersion) &&
      ['originalForm','replacementForm','originalBasis','replacementBasis'].every(key => named(binding[key]))) : null;
    return {lineIndex, original:clone(original), sourceQuantity:clone(original.sourceQuantity ?? null),
      parsedQuantity, sourceScaling:original.scaling ?? null,
      substitution:proposal ? {proposal:clone(proposal), binding, ...support} : null,
      selected:proposal ? (support.status === 'supported' ? clone(replacement) : null) : clone(original),
      // Original nutrient observations stay only in original; never transfer them.
      compositionAfterSubstitution:null,
      unknowns:['nutrient-composition-after-preparation', ...(parsedQuantity.basis === null ? ['quantity-basis'] : []),
        ...(parsedQuantity.form === null ? ['preparation-form'] : []), ...(proposal ? ['replacement-nutrient-composition'] : [])]};
  });
  let servingProjection = null;
  if (serving !== null) {
    const requested = clone(serving);
    const binding = {recipeId:source.id, recipeVersion, fraction:requested.fraction ?? null,
      form:requested.form ?? null, basis:requested.basis ?? null};
    const support = qualification(resolveScope, 'serving', binding, requested,
      requested.recipeId === source.id && equal(requested.recipeVersion, recipeVersion) && versioned(recipeVersion) &&
      typeof requested.fraction === 'number' && Number.isFinite(requested.fraction) &&
      requested.fraction > 0 && requested.fraction <= 1 && named(binding.form) && named(binding.basis));
    servingProjection = {requested, binding, ...support,
      qualifiedFraction:support.status === 'supported' ? requested.fraction : null};
  }
  return {projectionVersion:PREPARED_MENU_VERSION, recipeId:source.id, recipeVersion,
    sourceSnapshot:source, provenance:clone(source.provenance ?? null),
    sourceYield:clone(data.yield ?? null), finalBatchYield:clone(data.finalBatchYield ?? null),
    sourceServing:clone(data.serving ?? null), sourcePreparation:clone(data.preparation ?? null),
    sourceForm:data.form ?? null, sourceBasis:data.basis ?? null,
    serving:servingProjection, lines, nutrientComposition:null, cookingEligible:false,
    notice:'Source evidence projection only. No default yield, mass conversion, retention, nutrient or identity equivalence. Recipe production STOP and independent owner adoption review remain.'};
}

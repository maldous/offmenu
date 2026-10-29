import test from 'node:test';
import assert from 'node:assert/strict';
import {evaluateLabelScenario, SCENARIO_VERSION} from '../../tools/source-processing/gold-recipe-label-scenario.mjs';

const selected = {databaseSha256: 'a'.repeat(64), admissionSha256: 'b'.repeat(64)};
const support = (kind, target, scope) => [{target_kind: kind, target_id: target,
  support_scope: scope, citation_id: 'test:citation', evidence_sha256: 'c'.repeat(64)}];
function fixture() {
  const runId = 'recipe-actions:' + 'd'.repeat(64);
  const metric = {id: 'test:protein', name: 'Generated protein', unit: 'g', dimension: 'mass',
    state: 'verified', citationIds: ['test:citation'], supportRecords: support('metric', 'test:protein', 'definition')};
  const lines = [60, 30].map((massG, i) => {
    const id = 'test:product:' + i, ingredientId = 'test:ingredient:' + i;
    const basis = {kind: 'quantity', dimension: 'mass', value: 100, unitId: 'g'};
    const original = {kind: 'quantity', dimension: 'mass', value: [10, 20][i],
      sourceValue: String([10, 20][i]), unitId: 'g', sourceUnit: 'G', basis};
    const assertion = 'test:assertion:' + i;
    return {ingredientId, massG, massUnit: 'g',
      quantityEvidence: {runId, actionId: 'test:action:0', ingredientId, citationIds: ['test:citation'],
        allocation: {factor: '1', normalized_unit: 'g', original: {unit: 'g', value: String(massG)},
          scaled_min: String(massG), scaled_max: String(massG),
          normalized: {exact: true, status: 'normalized', unit: 'g', dimension: 'mass',
            original: {unit: 'g', value: String(massG)}, value: String(massG), issues: []}}},
      selection: {origin: 'GENERATED', productId: id, variantAssumption: 'Explicit test variant',
        massStateAssumption: 'Input mass of the labeled product only; no prepared yield'},
      product: {id, entityId: String(i + 1).repeat(64), domain: 'barcodes', type: 'barcode-product',
        state: 'verified', scope: {visibility: 'public'}, citationIds: ['test:citation']},
      observations: [{id: 'test:observation:' + i, entityId: String(i + 1).repeat(64),
        state: 'verified', metricId: metric.id, original,
        claim: {id: assertion, subjectId: id, propertyId: metric.id, value: original,
          scope: {visibility: 'public'}, citationIds: ['test:citation']},
        context: {basis, sourceDerivationCode: 'LCCS', method: 'Calculated from value per serving size measure',
          uncertainty: 'Generated source rounding; not assay', underlyingIndependentMeasurementCount: 0},
        supportRecords: support('assertion', assertion, 'field')} ]};
  });
  for (const [i, line] of lines.entries()) {
    const q = line.quantityEvidence;
    line.ingredientEntityId = String(i + 3).repeat(64); q.slotName = 'input' + i;
    const evidence = JSON.stringify([{pointer: '/steps/0/raw_text', start: 0, end: 3,
      text: 'Add', offset_unit: 'unicode_codepoint'}]);
    q.ingredientRecord = {run_id: q.runId, action_id: q.actionId, slot_name: q.slotName,
      source_ingredient_line_id: line.ingredientId, ingredient_entity_id: line.ingredientEntityId,
      allocation_json: JSON.stringify(q.allocation), evidence_json: evidence};
    q.ingredientSupport = [{run_id: q.runId, action_id: q.actionId, slot_name: q.slotName,
      citation_id: 'test:citation', evidence_json: evidence}];
  }
  return {schemaVersion: SCENARIO_VERSION, id: 'test:scenario', snapshot: {...selected},
    mode: 'GENERATED_SOURCE_LABEL_SCENARIO', recipe: {runId, repeatCount: 1,
      ingredientIds: lines.map(l => l.ingredientId)}, lines, metrics: [metric],
    citations: {'test:citation': {id: 'test:citation', license: 'Generated fixture', attribution: 'Test author'}},
    admissionLimits: {recipeNutritionTransferOrTotals: false}};
}
const evaluate = input => evaluateLabelScenario(input, selected);

test('source-label arithmetic reuses basket/1.1, retains provenance and never infers prepared yield', () => {
  const input = fixture(), before = structuredClone(input), result = evaluate(input);
  assert.equal(result.calculatorVersion, 'basket/1.1');
  assert.equal(result.state, 'CONDITIONAL_SOURCE_LABEL_ARITHMETIC');
  const metric = result.metrics['test:protein'];
  assert.equal(metric.conditionalInputSum, 12);
  assert.deepEqual(metric.contributions.map(c => c.value), [6, 6]);
  assert.deepEqual(metric.coverage, {qualifiedLines: 2, requiredLines: 2, inputMassFraction: 1});
  assert.deepEqual(result.inputs, before); assert.deepEqual(input, before);
  input.lines[0].massG = 999; assert.equal(result.inputs.lines[0].massG, 60);
  for (const key of ['actualRecipeNutrition', 'yieldG', 'servings', 'perServing', 'per100gPreparedFood']) assert.equal(result[key], null);
  assert.equal(result.actualUserSelection, false); assert.equal(result.sourceReferenceNutritionTransfer, false);
  assert.equal(result.automaticPlanning, false);
});

test('actual composition and absent or foreign product selection are held with no arithmetic', () => {
  for (const change of [x => x.mode = 'ACTUAL_RECIPE_COMPOSITION',
    x => x.lines.forEach(l => l.selection = null),
    x => x.lines.forEach(l => l.selection.productId = 'test:other'),
    x => x.lines.forEach(l => l.selection.origin = 'ACTUAL')]) {
    const input = fixture(); change(input); const result = evaluate(input);
    assert.equal(result.state, 'HELD');
    assert.equal(result.metrics['test:protein'].knownSubtotal, null);
    assert.equal(result.metrics['test:protein'].conditionalInputSum, null);
    assert.ok(result.holdReasons.length);
  }
});

test('missing source observation is partial, not zero; recorded zero remains a cited zero', () => {
  const input = fixture(); input.lines[0].observations = [];
  const partial = evaluate(input).metrics['test:protein'];
  assert.equal(partial.status, 'partial'); assert.equal(partial.knownSubtotal, 6);
  assert.equal(partial.conditionalInputSum, null); assert.equal(partial.contributions[0].value, null);
  assert.equal(partial.coverage.inputMassFraction, 1 / 3);
  const zero = input.lines[1].observations[0]; zero.original.value = 0; zero.original.sourceValue = '0.0';
  const result = evaluate(input).metrics['test:protein'];
  assert.equal(result.knownSubtotal, 0); assert.equal(result.contributions[1].value, 0);
  input.lines[1].observations = [];
  assert.equal(evaluate(input).metrics['test:protein'].knownSubtotal, null);
});

test('repeated action references, omitted ingredients and scaling cannot double count allocations', () => {
  for (const change of [x => x.lines.push(structuredClone(x.lines[0])), x => x.lines.pop(),
    x => x.recipe.repeatCount = 2, x => x.recipe.ingredientIds.push(x.recipe.ingredientIds[0])]) {
    const input = fixture(); change(input); assert.throws(() => evaluate(input), /once|ingredient/);
  }
  const input = fixture(); input.lines[0].quantityEvidence.allocation.factor = '2';
  assert.equal(evaluate(input).metrics['test:protein'].contributions[0].value, null);
});

test('held identity, mass, source-reference foods, mismatched units and unknown methods cannot contribute', () => {
  const changes = [l => l.massG = null, l => l.massUnit = 'ml', l => l.massG = -1,
    l => l.quantityEvidence.runId = 'foreign', l => l.quantityEvidence.allocation.scaled_max = '61',
    l => l.product.domain = 'ingredients', l => l.product.type = 'urn:offmenu:type:FoodPreparation',
    l => l.product.state = 'held', l => l.observations[0].entityId = '9'.repeat(64),
    l => l.observations[0].original.unitId = 'mg', l => l.observations[0].original.sourceValue = 'unknown',
    l => l.observations[0].original.basis.unitId = 'ml', l => l.observations[0].original.value = null,
    l => l.observations[0].context.sourceDerivationCode = 'UNKNOWN',
    l => l.observations[0].context.method = 'Analytical',
    l => l.observations[0].state = 'held', l => l.observations[0].supportRecords[0].evidence_sha256 = 'invalid',
    l => l.observations[0].supportRecords[0].target_id = 'foreign',
    l => l.observations[0].claim.subjectId = 'foreign'];
  for (const change of changes) {
    const input = fixture(); change(input.lines[0]);
    const result = evaluate(input).metrics['test:protein'];
    assert.equal(result.contributions[0].value, null, change.toString());
    assert.equal(result.conditionalInputSum, null); assert.equal(result.contributions[1].value, 6);
  }
});

test('ambiguous observations select no winner; distinct definition/citation rights must survive', () => {
  const input = fixture(); input.lines[0].observations.push(structuredClone(input.lines[0].observations[0]));
  assert.equal(evaluate(input).metrics['test:protein'].contributions[0].value, null);
  for (const change of [x => x.metrics[0].supportRecords[0].evidence_sha256 = 'invalid',
    x => x.metrics[0].supportRecords[0].support_scope = 'field',
    x => x.citations['test:citation'].license = '',
    x => x.citations['test:citation'].attribution = '']) {
    const value = fixture(); change(value);
    assert.equal(evaluate(value).metrics['test:protein'].knownSubtotal, null);
  }
  const value = fixture(); value.citations['test:definition'] = {id: 'test:definition', license: 'Distinct license', attribution: 'Definition author'};
  value.metrics[0].citationIds = ['test:definition']; value.metrics[0].supportRecords[0].citation_id = 'test:definition';
  assert.deepEqual(evaluate(value).inputs.citations['test:definition'], value.citations['test:definition']);
});

test('snapshot selection, nonfinite values and structural/count/byte limits fail closed', () => {
  const input = fixture(); input.snapshot.databaseSha256 = 'f'.repeat(64);
  assert.throws(() => evaluate(input), /selected-snapshot/);
  for (const value of [NaN, Infinity]) {
    const input = fixture(); input.lines[0].massG = value; assert.throws(() => evaluate(input), /finite-json/);
  }
  const tooMany = fixture(); tooMany.lines = Array(9).fill(tooMany.lines[0]);
  assert.throws(() => evaluate(tooMany), /count-limit/);
  const huge = fixture(); huge.id = 'x'.repeat(524288); assert.throws(() => evaluate(huge), /byte-limit/);
  const cycle = fixture(); cycle.loop = cycle; assert.throws(() => evaluate(cycle), /json-required/);
});


test('native quantity support binds exact run, action, slot, source ingredient and evidence', () => {
  const changes = [
    q => q.ingredientSupport = [],
    q => q.actionId = 'test:foreign-action',
    q => q.ingredientSupport[0].run_id = 'recipe-actions:' + 'f'.repeat(64),
    q => q.ingredientSupport[0].slot_name = 'foreign-slot',
    q => q.ingredientSupport[0].evidence_json = '[]',
    q => q.allocation.normalized.dimension = 'volume',
    q => delete q.ingredientRecord,
    q => q.ingredientRecord.run_id = 'recipe-actions:' + 'e'.repeat(64),
    q => q.ingredientRecord.source_ingredient_line_id = 'test:foreign-ingredient',
    q => q.ingredientRecord.ingredient_entity_id = 'f'.repeat(64),
    q => q.ingredientRecord.allocation_json = 'null', // A later qualitative reference is not another debit.
    q => q.ingredientRecord.allocation_json = 'invalid',
    q => q.ingredientRecord.evidence_json = '[]',
    q => q.ingredientSupport[0].citation_id = 'test:foreign-citation',
    q => q.ingredientSupport[0].action_id = 'test:foreign-action',
    q => q.ingredientSupport.push(structuredClone(q.ingredientSupport[0])),
    q => q.ingredientSupport[0].evidence_json = JSON.stringify([{pointer: '/steps/0/raw_text',
      start: 1, end: 4, text: 'Add', offset_unit: 'unicode_codepoint'}])
  ];
  for (const change of changes) {
    const input = fixture(); change(input.lines[0].quantityEvidence);
    const result = evaluate(input).metrics['test:protein'];
    assert.equal(result.contributions[0].value, null, change.toString());
    assert.ok(result.contributions[0].holdReasons.length);
    assert.equal(result.contributions[1].value, 6);
    assert.equal(result.knownSubtotal, 6); assert.equal(result.conditionalInputSum, null);
  }
});

test('a coherent but non-mass allocation cannot qualify, and valid record order is immaterial', () => {
  const input = fixture(), q = input.lines[0].quantityEvidence;
  q.allocation.normalized.dimension = 'volume';
  q.ingredientRecord.allocation_json = JSON.stringify(q.allocation);
  assert.equal(evaluate(input).metrics['test:protein'].contributions[0].value, null);
  const valid = fixture();
  valid.lines[0].quantityEvidence.ingredientRecord.allocation_json = JSON.stringify(
    Object.fromEntries(Object.entries(valid.lines[0].quantityEvidence.allocation).reverse()));
  assert.equal(evaluate(valid).metrics['test:protein'].conditionalInputSum, 12);
  const record = valid.lines[0].quantityEvidence.ingredientRecord;
  assert.equal(record.source_ingredient_line_id, valid.lines[0].ingredientId);
  assert.equal(record.action_id, valid.lines[0].quantityEvidence.actionId);
});

test('native evidence uses Unicode codepoint offsets, not UTF16 width or empty markers', () => {
  const input = fixture(), q = input.lines[0].quantityEvidence;
  const spans = [{pointer: '/steps/0/raw_text', start: 4, end: 5, text: '🥣', offset_unit: 'unicode_codepoint'}];
  q.ingredientRecord.evidence_json = q.ingredientSupport[0].evidence_json = JSON.stringify(spans);
  assert.equal(evaluate(input).metrics['test:protein'].conditionalInputSum, 12);
  spans[0].end = 6;
  q.ingredientRecord.evidence_json = q.ingredientSupport[0].evidence_json = JSON.stringify(spans);
  const metric = evaluate(input).metrics['test:protein'];
  assert.equal(metric.contributions[0].value, null); assert.equal(metric.contributions[1].value, 6);
});

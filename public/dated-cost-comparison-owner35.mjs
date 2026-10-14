// NORM-09: injected dated evidence only. No offers, pack rounding or source admission.
const VERSION = 'dated-cost-comparison/1';
const named = x => typeof x === 'string' && x.trim().length > 0 && x.length <= 200;
const currency = x => typeof x === 'string' && /^[A-Z]{3}$/.test(x);
const date = x => typeof x === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(x) &&
  Number.isFinite(Date.parse(x + 'T12:00:00Z')) && new Date(x + 'T12:00:00Z').toISOString().slice(0, 10) === x;

function capture(input) {
  let nodes = 0, chars = 0;
  const active = new WeakSet();
  function copy(v, depth = 0) {
    if (++nodes > 100000 || depth > 32) throw Error('Capture bounds exceeded');
    if (v === null || typeof v === 'boolean') return v;
    if (typeof v === 'string') { chars += v.length; if (chars > 2000000) throw Error('Capture bounds exceeded'); return v; }
    if (typeof v === 'number' && Number.isFinite(v)) return v;
    if (!v || typeof v !== 'object' || active.has(v)) throw Error('Plain finite JSON required');
    const array = Array.isArray(v), proto = Object.getPrototypeOf(v);
    if (proto !== (array ? Array.prototype : Object.prototype) && !(proto === null && !array)) throw Error('Plain finite JSON required');
    const fields = Object.getOwnPropertyDescriptors(v), keys = Reflect.ownKeys(fields);
    if (keys.some(k => typeof k !== 'string')) throw Error('Plain finite JSON required');
    if (array && (v.length > 10000 || keys.length !== v.length + 1 ||
      Array.from({length:v.length}, (_, i) => String(i)).some(k => !Object.hasOwn(fields, k)))) throw Error('Dense arrays required');
    active.add(v);
    const entries = [];
    for (const k of keys) {
      if (array && k === 'length') continue;
      chars += k.length; if (chars > 2000000) throw Error('Capture bounds exceeded');
      const d = fields[k];
      if (!Object.hasOwn(d, 'value') || !d.enumerable) throw Error('Own data required');
      entries.push([k, copy(d.value, depth + 1)]);
    }
    active.delete(v);
    return array ? entries.map(([, value]) => value) : Object.fromEntries(entries.sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0));
  }
  return copy(input);
}
function immutable(v) {
  if (v && typeof v === 'object') { for (const x of Object.values(v)) immutable(x); Object.freeze(v); }
  return v;
}
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const gcd = (a, b) => b === 0n ? a : gcd(b, a % b);
const rational = (n, d = 1n) => { const g = gcd(n, d); return {n:n / g, d:d / g}; };
const add = (a, b) => rational(a.n * b.d + b.n * a.d, a.d * b.d);
const multiply = (a, b) => rational(a.n * b.n, a.d * b.d);
const divide = (a, b) => rational(a.n * b.d, a.d * b.n);
const compare = (a, b) => a.n * b.d < b.n * a.d ? -1 : a.n * b.d > b.n * a.d ? 1 : 0;
function decimal(value, positive = false) {
  if (typeof value !== 'string' || !/^(0|[1-9]\d{0,11})(\.\d{1,6})?$/.test(value)) return null;
  const [whole, fraction = ''] = value.split('.');
  const result = rational(BigInt(whole + fraction), 10n ** BigInt(fraction.length));
  return positive && result.n === 0n ? null : result;
}
const MAX = rational(1000000000000n);
function output(value) {
  if (compare(value, MAX) > 0 || value.n.toString().length > 120 || value.d.toString().length > 120) return null;
  // Recurring decimals retain exact fractions; never silently round or emit Infinity.
  const scaled = value.n * 1000000n;
  let text = null;
  if (scaled % value.d === 0n) {
    const digits = (scaled / value.d).toString().padStart(7, '0');
    text = (digits.slice(0, -6) + '.' + digits.slice(-6)).replace(/\.?0+$/, '');
  }
  return {numerator:value.n.toString(), denominator:value.d.toString(), decimal:text};
}
const promiseThen = Promise.prototype.then;
function observeAsync(value) {
  try {
    // The intrinsic checks genuine Promise internal slots across realms before
    // using its handlers. Never look up value.then or assimilate plain thenables.
    Reflect.apply(promiseThen, value, [() => {}, () => {}]);
    return true;
  } catch { return false; }
}
function qualified(resolve, kind, binding) {
  try {
    const raw = resolve(immutable(capture({kind, binding})));
    if (observeAsync(raw)) return {ok:false, evidence:null, reason:'asynchronous-evidence'};
    const evidence = raw == null ? null : capture(raw), p = evidence?.provenance;
    if (evidence?.then) return {ok:false, evidence:null, reason:'asynchronous-evidence'};
    const ok = evidence?.status === 'qualified' && same(evidence.binding, binding) && named(p?.sourceId) &&
      named(p?.version) && typeof p?.sha256 === 'string' && /^[a-f0-9]{64}$/.test(p.sha256) && p?.rights?.derivedUse === true;
    return {ok, evidence, reason:ok ? null : evidence?.status === 'conflict' ? 'conflicting-evidence' : 'unqualified-evidence'};
  } catch { return {ok:false, evidence:null, reason:'evidence-resolution-failed'}; }
}
const quantity = q => q && ['g', 'ml', 'count'].includes(q.unit) && decimal(q.value, true);

/** Trusted resolveEvidence must qualify exact captured bindings, current source rights,
 * specifications and observation conditions. Client flags are not qualification.
 * Every candidate describes the SAME cohort quantities; different geography is explicit.
 */
export function compareDatedCosts(input, {resolveEvidence = () => null} = {}) {
  if (typeof resolveEvidence !== 'function') throw TypeError('Evidence resolver required');
  const request = capture(input), {cohort, candidates, rates = []} = request;
  if (!cohort || !['local', 'fx', 'ppp'].includes(request.view) ||
      request.purpose !== (request.view === 'ppp' ? 'ppp-analysis' : 'dated-price-comparison') ||
      !Array.isArray(candidates) || !candidates.length || candidates.length > 50 ||
      !Array.isArray(rates) || rates.length > 100 || !Array.isArray(cohort.quantities) ||
      !cohort.quantities.length || cohort.quantities.length > 100 ||
      !['source-price-observation', 'published-basic-needs', 'recipe-modelled'].includes(cohort.evidenceTrack) ||
      !['pack', 'consumed'].includes(cohort.amountBasis) ||
      !['id', 'version', 'specificationId', 'specificationVersion', 'population', 'foodState'].every(k => named(cohort[k])) ||
      !date(cohort.date) || !date(cohort.period?.start) || !date(cohort.period?.end) ||
      cohort.period.start > cohort.date || cohort.date > cohort.period.end ||
      !named(cohort.channel) || !named(cohort.conditions?.delivery) || !named(cohort.conditions?.promotion) ||
      !named(cohort.conditions?.loyalty) || cohort.conditions?.tax !== 'included' ||
      !decimal(cohort.comparisonResolution, true) ||
      (request.view === 'ppp' ? request.targetCurrency !== 'international-dollar' || cohort.level !== 'aggregate-basket' : !currency(request.targetCurrency)))
    throw TypeError('Bounded dated same-specification cohort required');
  const ids = new Set(), requiredIds = new Set();
  for (const q of cohort.quantities) {
    if (!named(q.id) || requiredIds.has(q.id)) throw TypeError('Unique specification line IDs required');
    requiredIds.add(q.id);
  }
  const rows = [], comparable = [], allBlockers = [];
  for (const candidate of candidates) {
    if (!candidate || !named(candidate.id) || ids.has(candidate.id) || !Array.isArray(candidate.lines) || candidate.lines.length > 100)
      throw TypeError('Unique bounded candidates required');
    ids.add(candidate.id);
    const blockers = [], block = reason => { if (!blockers.includes(reason)) blockers.push(reason); };
    if (!named(candidate.geography?.country) || !named(candidate.geography?.region) || !named(candidate.outlet)) block('geography-or-outlet-unknown');
    if (candidate.date !== cohort.date || !date(candidate.date) || !same(candidate.period, cohort.period)) block('incompatible-date-or-period');
    if (!currency(candidate.currency) || candidate.channel !== cohort.channel || !same(candidate.conditions, cohort.conditions)) block('incompatible-price-conditions');
    const lineMap = new Map();
    for (const line of candidate.lines) {
      if (!line || !requiredIds.has(line.id) || lineMap.has(line.id)) throw TypeError('Unique cohort price lines required');
      lineMap.set(line.id, line);
    }
    let subtotal = rational(0n); const lines = [], unknown = [], coverage = {};
    for (const required of cohort.quantities) {
      const line = lineMap.get(required.id), requiredAmount = quantity(required.quantity);
      const reasons = [];
      if (!requiredAmount) reasons.push('quantity-or-unit-unknown');
      if (!line || !same(line.quantity, required.quantity)) reasons.push('specification-quantity-mismatch');
      if (!line || line.cost?.basis !== cohort.amountBasis || line.cost?.currency !== candidate.currency) reasons.push('incompatible-cost-basis');
      const amount = decimal(line?.cost?.value);
      if (!amount) reasons.push('cost-or-precision-unknown');
      const binding = capture({purpose:request.purpose, cohort, candidateId:candidate.id, geography:candidate.geography ?? null,
        date:candidate.date ?? null, period:candidate.period ?? null, outlet:candidate.outlet ?? null,
        currency:candidate.currency ?? null, channel:candidate.channel ?? null, conditions:candidate.conditions ?? null, line:line ?? null});
      const evidence = line ? qualified(resolveEvidence, 'price', binding) : {ok:false, evidence:null, reason:'price-line-absent'};
      if (!evidence.ok) reasons.push(evidence.reason);
      const known = reasons.length === 0;
      if (known) subtotal = add(subtotal, amount); else unknown.push(required.id);
      const unit = required.quantity?.unit;
      if (['g', 'ml', 'count'].includes(unit)) {
        const group = coverage[unit] ??= {required:rational(0n), known:rational(0n), unresolved:[]};
        if (requiredAmount) { group.required = add(group.required, requiredAmount); if (known) group.known = add(group.known, requiredAmount); }
        else group.unresolved.push(required.id);
      }
      lines.push({id:required.id, status:known ? 'known' : 'unknown', reasons, source:line ?? null, qualification:evidence.evidence});
    }
    if (unknown.length) block('incomplete-price-coverage');
    if (!output(subtotal)) block('aggregate-out-of-range');
    if (Object.values(coverage).some(g => !output(g.required) || !output(g.known))) block('quantity-aggregate-out-of-range');
    let total = subtotal, conversion = null;
    if (request.view === 'local' && candidate.currency !== request.targetCurrency) block('currency-mismatch');
    if (request.view === 'ppp' || request.view === 'fx' && candidate.currency !== request.targetCurrency) {
      const matching = rates.filter(r => r?.from === candidate.currency && r?.to === request.targetCurrency &&
        (request.view !== 'ppp' || same(r.geography, candidate.geography)));
      if (matching.length !== 1) block(matching.length ? 'ambiguous-rate' : 'rate-missing');
      else {
        const rate = matching[0], factor = decimal(rate.value, true);
        const right = request.view === 'fx'
          ? rate.direction === 'target-per-source' && rate.date === candidate.date && date(rate.date)
          : rate.direction === 'local-per-international-dollar' && named(rate.series) && named(rate.component) &&
            named(rate.methodology) && Number.isInteger(rate.referenceYear) &&
            String(rate.referenceYear) === cohort.date.slice(0, 4) &&
            cohort.period.start.slice(0, 4) === cohort.date.slice(0, 4) && cohort.period.end.slice(0, 4) === cohort.date.slice(0, 4) &&
            same(rate.geography, candidate.geography);
        const evidence = qualified(resolveEvidence, request.view, capture({purpose:request.purpose, cohort, candidateId:candidate.id,
          geography:candidate.geography ?? null, date:candidate.date ?? null, rate}));
        conversion = {source:rate, qualification:evidence.evidence};
        if (!factor || rate.purpose !== request.purpose || !named(rate.id) || !named(rate.version) || !right || !evidence.ok) block('unqualified-or-incompatible-rate');
        else total = request.view === 'fx' ? multiply(total, factor) : divide(total, factor);
      }
    }
    const denom = cohort.denominator; let denominatorEvidence = null;
    const denominatorValid = denom?.kind === 'basket' && denom.unit === 'basket' && denom.value === '1' ||
      cohort.amountBasis === 'consumed' && (denom?.kind === 'person-days' && denom.unit === 'person-day' || denom?.kind === 'energy' && denom.unit === 'kcal') && decimal(denom.value, true);
    if (!denominatorValid) block('denominator-missing-or-incompatible');
    else {
      const evidence = qualified(resolveEvidence, 'denominator', capture({purpose:request.purpose, cohort, denominator:denom}));
      denominatorEvidence = evidence.evidence;
      if (!evidence.ok) block('denominator-unqualified');
      else if (denom.kind !== 'basket') total = divide(multiply(total, rational(denom.kind === 'energy' ? 1000n : 1n)), decimal(denom.value, true));
    }
    const exact = output(total); if (!exact) block('aggregate-out-of-range');
    for (const reason of blockers) allBlockers.push({candidateId:candidate.id, reason});
    rows.push({id:candidate.id, status:blockers.length ? 'blocked' : 'comparable', blockers, lines,
      knownSubtotal:{currency:candidate.currency ?? null, amountBasis:cohort.amountBasis, value:output(subtotal)},
      // Per-candidate complete values are withheld when ANY cohort member is incomplete below.
      total:blockers.length ? null : exact, conversion, denominatorQualification:denominatorEvidence,
      coverage:{requiredLines:cohort.quantities.length, knownLines:cohort.quantities.length - unknown.length, unknownLineIds:unknown,
        byUnit:Object.fromEntries(Object.entries(coverage).map(([unit, g]) => [unit, {known:output(g.known), required:g.unresolved.length ? null : output(g.required), unresolvedQuantityLineIds:g.unresolved}]))}});
    if (!blockers.length) comparable.push({id:candidate.id, value:total});
  }
  let ranking = null;
  if (!allBlockers.length) {
    comparable.sort((a, b) => compare(a.value, b.value));
    const resolution = decimal(cohort.comparisonResolution, true), groups = [];
    for (const item of comparable) {
      const group = groups.at(-1);
      // Chain neighbouring indistinguishable amounts into a conservative tie group.
      if (group && compare(item.value, add(group.last, resolution)) <= 0) { group.ids.push(item.id); group.last = item.value; }
      else groups.push({last:item.value, ids:[item.id]});
    }
    ranking = groups.map(g => g.ids);
  } else for (const row of rows) row.total = null;
  const result = {version:VERSION, view:request.view, purpose:request.purpose, sourceSnapshot:request,
    status:allBlockers.length ? 'blocked' : 'complete', currency:request.targetCurrency,
    metric:{amountBasis:cohort.amountBasis, denominator:cohort.denominator ?? null,
      scaling:cohort.denominator?.kind === 'energy' ? 'per-1000-kcal' : cohort.denominator?.kind === 'person-days' ? 'per-person-day' : 'per-basket'},
    rows, blockers:allBlockers, ranking, comparisonResolution:cohort.comparisonResolution,
    notice:'Dated source arithmetic only; known subtotals are incomplete evidence, not totals. PPP is analytical context, never checkout currency. No source admission, current quote, recommendation, purchase or production activation.'};
  if (new TextEncoder().encode(JSON.stringify(result)).length > 8000000) throw Error('Projection output bounds exceeded');
  return immutable(result);
}

import {getLanguage, t} from './i18n.js';

const localeKey = value => String(value || 'und').replaceAll('_', '-').toLowerCase();
const text = value => typeof value === 'string' && value.trim() ? value : null;
const aliases = {name:'names', title:'titles', ingredient:'names', originalText:'originalTexts', ingredientsText:'ingredientsTexts', instructions:'instructionsByLanguage', directions:'directionsByLanguage'};
let corpusResolver;
// The corpus owner supplies this adapter once its universal representation is
// finalized. This presentation module does not define or migrate that schema.
export function configureCorpusResolver(resolver) {
  if (resolver != null && typeof resolver !== 'function') throw new TypeError('A corpus resolver must be a function.');
  corpusResolver = resolver;
}

// Display projections never replace canonical ingredient IDs, source text,
// quantities, instructions or provenance in the stored record.
export function localizedField(record, field = 'name', locale = getLanguage()) {
  const projection = corpusResolver?.(record, field, locale);
  if (projection) return projection;
  const data = record?.data || record || {};
  const sourceLanguage = localeKey(data.language || data.lang || data.languages?.[0]);
  const original = (field === 'name' ? data.sourceName : undefined) ?? data[field] ?? (field === 'name' ? data.title ?? data.foodName ?? data.ingredient : undefined) ?? '';
  const variants = new Map();
  for (const [language, value] of Object.entries(data[aliases[field] || field + 'ByLanguage'] || {})) {
    if (text(value) || Array.isArray(value) && value.every(v => typeof v === 'string')) variants.set(localeKey(language), value);
  }
  for (const [language, fields] of Object.entries(data.translations || {})) {
    const value = fields?.[field];
    if (text(value) || Array.isArray(value) && value.every(v => typeof v === 'string')) variants.set(localeKey(language), value);
  }
  const requested = localeKey(locale);
  const match = requested === 'native' ? null : [requested, requested.split('-')[0]].find(key => variants.has(key));
  const sourceMatches = requested === sourceLanguage || requested.split('-')[0] === sourceLanguage.split('-')[0];
  const value = match ? variants.get(match) : original;
  return {value, original, language:match || sourceLanguage, requested,
    translated:!!match && !sourceMatches,
    missingTranslation:requested !== 'native' && !match && !sourceMatches,
    availableLanguages:[...new Set([sourceLanguage, ...variants.keys()])].filter(code => code !== 'und')};
}

export function displayName(record, locale = getLanguage()) {
  return localizedField(record, record?.title && !record?.name && !record?.data ? 'title' : 'name', locale).value;
}
export function localizedLotName(lot, products = {}, locale = getLanguage()) {
  const own = localizedField(lot, 'name', locale);
  const product = products[lot.barcode];
  // Barcode-linked publisher labels can translate an unchanged product name.
  // Personal renames and explicit lot translations take precedence.
  return product && lot.name === product.name && !own.resourceId && !own.availableLanguages?.length
    ? localizedField(product, 'name', locale) : own;
}
export function localizedRecipe(record, locale = getLanguage()) {
  const data = record?.data || record;
  const title = localizedField(record, data.title != null ? 'title' : 'name', locale);
  const instructionField = data.directions ? 'directions' : 'instructions';
  const directions = localizedField(record, instructionField, locale);
  return {title, directions, ingredients:(data.ingredients || []).map(item => ({
    source:item,
    name:localizedField({...item, name:item.name || item.ingredient, language:item.language || data.language || data.languages?.[0]}, 'name', locale),
    originalText:localizedField({...item, language:item.language || data.language || data.languages?.[0]}, 'originalText', locale),
  }))};
}
export function showLocalized(element, field) {
  element.textContent = field.value;
  element.lang = field.language;
  element.dir = 'auto';
  const notice = field.fallbackReason === 'stale'
    ? 'Translation is stale; showing the original source text.' : 'Translation unavailable; showing the original source text.';
  element.title = field.missingTranslation ? t(notice) : '';
  if (field.missingTranslation) {
    element.dataset.translationFallback = 'true';
    element.dataset.translationFallbackReason = field.fallbackReason || 'missing';
  } else {
    delete element.dataset.translationFallback;
    delete element.dataset.translationFallbackReason;
  }
}
export function showUserText(element, value) {
  element.textContent = String(value ?? '');
  element.dir = 'auto';
  element.lang = 'und';
}
export function multilingualSearchText(record) {
  const data = record?.data || record || {};
  const values = [];
  const collect = value => {
    if (typeof value === 'string') values.push(value);
    else if (Array.isArray(value)) value.forEach(collect);
    else if (value && typeof value === 'object') Object.values(value).forEach(collect);
  };
  for (const key of ['name','title','foodName','names','titles','translations','directions','instructions','directionsByLanguage','instructionsByLanguage']) collect(data[key]);
  for (const item of data.ingredients || []) {
    for (const key of ['name','ingredient','ingredientId','originalText','names','originalTexts','translations']) collect(item[key]);
  }
  if (!values.length) collect(data.search);
  return normalizeSearchText(values.join(' '));
}
// Strip accents only from Latin letters. Removing all Unicode combining marks
// corrupts Japanese voicing and significant marks in other scripts.
export function normalizeSearchText(value) {
  return String(value || '').normalize('NFD').replace(/([\p{Script=Latin}])\p{M}+/gu,'$1').normalize('NFC').toLowerCase().trim();
}

import {ARABIC} from './locales/ar.js';

export const LANGUAGES = Object.freeze([
  {code:'en', name:'English', direction:'ltr'},
  {code:'ar', name:'العربية', direction:'rtl'},
]);
export const LANGUAGE_KEY = 'offmenu-ui-language-v1';
const CATALOGUES = {ar:ARABIC};
const renderedLanguages = new Map();
let language = 'en';

export function resolveLanguage(preferred = []) {
  for (const value of Array.isArray(preferred) ? preferred : [preferred]) {
    const code = String(value || '').toLowerCase().split(/[-_]/)[0];
    if (LANGUAGES.some(item => item.code === code)) return code;
  }
  return 'en';
}
export function getLanguage() { return language; }
export function setLanguage(value) { language = resolveLanguage(value); renderedLanguages.clear(); return language; }
export function languageDirection(locale = language) {
  return LANGUAGES.find(item => item.code === resolveLanguage(locale)).direction;
}
export function hasTranslation(key, locale = language) {
  return locale === 'en' || Object.hasOwn(CATALOGUES[locale] || {}, key);
}
// English messages are catalogue keys. Interpolation is plain text, never HTML.
export function t(key, values = {}, locale = language) {
  if (typeof key === 'number') return new Intl.NumberFormat(locale, {maximumFractionDigits:20}).format(key);
  const source = String(key ?? '');
  const catalogue = CATALOGUES[locale] || {};
  const entry = Object.hasOwn(catalogue, source) ? catalogue[source] : source;
  const category = Number.isFinite(values.count) ? new Intl.PluralRules(locale).select(values.count) : 'other';
  const message = typeof entry === 'string' ? entry : entry[category] || entry.other || source;
  const output = message.replace(/\{([\w]+)\}/g, (match, name) =>
    Object.hasOwn(values, name) ? typeof values[name] === 'number'
      ? new Intl.NumberFormat(locale, {maximumFractionDigits:20}).format(values[name])
      : String(values[name]) : match);
  const previous = renderedLanguages.get(source);
  const outputLanguage = Object.hasOwn(catalogue, source) ? locale
    : previous && !Object.keys(values).length ? previous : 'en';
  if (renderedLanguages.size >= 2000) renderedLanguages.delete(renderedLanguages.keys().next().value);
  renderedLanguages.set(output, outputLanguage);
  return output;
}
export function renderedLanguage(value) { return renderedLanguages.get(String(value)); }
export function setLocalizedText(element, key, values = {}, locale = language) {
  const output = t(key, values, locale);
  element.textContent = output;
  element.lang = typeof key === 'number' ? locale : renderedLanguage(output) || 'en';
  element.dir = 'auto';
}
export function formatCurrency(value, currency) {
  return new Intl.NumberFormat(language, {style:'currency', currency, maximumFractionDigits:20}).format(value);
}
export function apiError(payload, fallback = 'Operation unavailable.') {
  const key = payload?.messageId || payload?.error || fallback;
  const values = payload?.messageValues || {};
  const error = new Error(t(key, values));
  // Sync decisions and diagnostics must not depend on the translated message.
  error.sourceMessage = t(key, values, 'en');
  error.code = payload?.errorCode;
  return error;
}
export function formatNumber(value, options = {}) {
  return new Intl.NumberFormat(language, options).format(value);
}
export function formatDate(value, options = {}) {
  const date = typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value)
    ? new Date(value + 'T12:00:00') : new Date(value);
  return new Intl.DateTimeFormat(language, options).format(date);
}
export function countryName(code) { return new Intl.DisplayNames([language], {type:'region'}).of(code); }

export function translateUI(root = document) {
  root.documentElement.lang = language;
  root.documentElement.dir = languageDirection();
  for (const element of root.querySelectorAll('[data-i18n]')) {
    const key = element.getAttribute('data-i18n');
    element.textContent = t(key);
    // Screen readers can pronounce untranslated English correctly in an Arabic UI.
    element.lang = hasTranslation(key) ? language : 'en';
  }
  for (const attribute of ['aria-label', 'placeholder', 'title', 'alt', 'content']) {
    for (const element of root.querySelectorAll('[data-i18n-' + attribute + ']')) {
      element.setAttribute(attribute, t(element.getAttribute('data-i18n-' + attribute)));
    }
  }
}
export function setupLanguage(root = document, storage, browser = globalThis.navigator) {
  let saved;
  try { storage ??= globalThis.localStorage; saved = storage?.getItem(LANGUAGE_KEY); } catch { /* A URL preference also works with storage disabled. */ }
  const requested = new URL(globalThis.location?.href || 'https://offmenu.invalid/').searchParams.get('uiLanguage');
  setLanguage(requested || saved || browser?.languages || browser?.language || 'en');
  translateUI(root);
  const manifest = root.querySelector('link[rel="manifest"]');
  if (manifest) manifest.href = language === 'ar' ? '/manifest-ar.webmanifest' : '/manifest.webmanifest';
  for (const select of root.querySelectorAll('[data-ui-language]')) {
    select.value = language;
    select.addEventListener('change', () => {
      const previous = language;
      const next = resolveLanguage(select.value);
      try { storage?.setItem(LANGUAGE_KEY, next); } catch { /* Retain the preference in the URL. */ }
      // Reinitialize every dynamic view in the selected locale. Pantry, account,
      // recipe and checkout data already persist independently of this preference.
      if (next !== previous) {
        const url = new URL(globalThis.location.href);
        url.searchParams.set('uiLanguage', next);
        globalThis.location.assign(url.href);
      }
    });
  }
  return language;
}

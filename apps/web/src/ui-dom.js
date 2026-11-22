import {renderedLanguage} from './i18n.js';

export const byId = id => document.getElementById(id);

// Dynamic labels carry the language selected by the message renderer.
export function localizedElement(tag, content, className) {
  const element = document.createElement(tag);
  element.textContent = content;
  const language = renderedLanguage(content);
  if (language) element.lang = language;
  element.dir = 'auto';
  if (className) element.className = className;
  return element;
}

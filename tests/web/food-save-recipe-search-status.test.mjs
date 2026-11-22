import assert from 'node:assert/strict';
import test from 'node:test';
import {getLanguage, setLanguage} from '../../apps/web/src/i18n.js';
import {setupJourney} from '../../apps/web/src/journey-ui.js';

function foodFixture(context, {ingredient = 'carrots', language = 'en', refuseCommit = false, findMeals = true} = {}) {
  const previousLanguage = getLanguage();
  const previousDocument = Object.getOwnPropertyDescriptor(globalThis, 'document');
  context.after(() => {
    setLanguage(previousLanguage);
    if (previousDocument) Object.defineProperty(globalThis, 'document', previousDocument);
    else delete globalThis.document;
  });
  setLanguage(language);

  const controls = new Map();
  const events = [];
  const makeElement = id => ({
    value: '', textContent: '', open: false, children: [],
    append(...children) { this.children.push(...children); },
    replaceChildren(...children) { this.children = children; },
    querySelector() { return {open: false}; },
    reset() {},
    addEventListener() {},
    showModal() { this.open = true; },
    close() { this.open = false; events.push(['close', id]); },
    focus() { events.push(['focus', id]); }
  });
  const element = id => {
    if (!controls.has(id)) controls.set(id, makeElement(id));
    return controls.get(id);
  };
  Object.defineProperty(globalThis, 'document', {
    configurable: true,
    value: {getElementById: element, createElement: makeElement, querySelectorAll: () => []}
  });

  const profile = {locations: [{area: 'Pantry', shelf: 'A'}]};
  let inventory = [];
  const journey = setupJourney({
    getData: () => ({profile, inventory}),
    commit: update => {
      if (refuseCommit) throw new Error('Synthetic save not available');
      inventory = update.inventory;
      events.push(['save', inventory.length]);
    },
    today: () => '2026-11-22',
    view: name => events.push(['view', name, element('menu-search').value])
  });
  journey.openFood(findMeals);
  for (const [id, value] of Object.entries({
    'food-name': 'Food fixture', 'food-ingredient': ingredient,
    'food-quantity': '125', 'food-unit': 'g', 'food-location': element('food-location').children[0].value
  })) element(id).value = value;
  return {
    element, events, inventory: () => inventory,
    submit() {
      let prevented = false;
      element('food-form').onsubmit({preventDefault() { prevented = true; }});
      assert.equal(prevented, true);
    }
  };
}

test('saving food and opening Meals describes a search, not a successful recipe match', context => {
  const f = foodFixture(context);
  f.submit();
  assert.deepEqual(f.events, [
    ['save', 1], ['close', 'food-dialog'], ['view', 'meals', 'carrot'], ['focus', 'menu-notice']
  ]);
  assert.equal(f.inventory()[0].ingredient, 'carrot');
  assert.equal(f.inventory()[0].quantity, 125);
  assert.equal(f.element('menu-notice').textContent, 'Saved Food fixture in Pantry / A. Searched recipes for carrot.');
});

test('Arabic selection retains the English fallback language for the neutral save/search status', context => {
  const f = foodFixture(context, {language: 'ar'});
  f.submit();
  assert.equal(getLanguage(), 'ar');
  const notice = f.element('menu-notice');
  assert.equal(notice.textContent, 'Saved Food fixture in Pantry / A. Searched recipes for carrot.');
  assert.equal(notice.lang, 'en');
  assert.equal(notice.dir, 'auto');
});

test('unmapped food retains its separate review status and searches its label', context => {
  const f = foodFixture(context, {ingredient: ''});
  f.submit();
  assert.equal(f.inventory()[0].needsReview, true);
  assert.equal(f.element('menu-search').value, 'Food fixture');
  assert.match(f.element('menu-notice').textContent, /Confirm its ingredient in Kitchen/);
});

test('refused saving does not close, search, focus the notice, or claim success', context => {
  const f = foodFixture(context, {refuseCommit: true});
  f.submit();
  assert.deepEqual(f.events, []);
  assert.deepEqual(f.inventory(), []);
  assert.equal(f.element('food-dialog').open, true);
  assert.equal(f.element('food-notice').textContent, 'Synthetic save not available');
  assert.equal(f.element('menu-notice').textContent, '');
});

test('ordinary food save still returns to shelves rather than announcing a recipe search', context => {
  const f = foodFixture(context, {findMeals: false});
  f.submit();
  assert.deepEqual(f.events, [['save', 1], ['close', 'food-dialog'], ['view', 'shelves', '']]);
  assert.equal(f.element('menu-notice').textContent, '');
});

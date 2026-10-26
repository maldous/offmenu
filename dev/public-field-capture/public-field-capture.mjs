// Public field selection is the disclosure boundary. Keys inside a selected
// value are source data, including language tags and nutrient identifiers.
export const PUBLIC_FIELDS = Object.freeze([
  'name', 'names', 'brand', 'packageQuantity', 'servingQuantity', 'dataType',
  'ingredientDeclaration', 'categories', 'sourceAllergenClaims',
  'sourceTraceClaims', 'sourceDietaryLabelClaims', 'origins',
  'manufacturingPlaces', 'rawNutriments', 'nutritionSourceBasis', 'markets',
  'nutrientProfile', 'sourceProvenance',
]);
const BINDING_KEYS = Object.freeze([
  'observationKey', 'sourceObservation', 'sourceBinding', 'referenceRecordId',
  'exactObservationBridge',
]);
const encoder = new TextEncoder();

function copyJSON(value, depth, budget) {
  if (++budget.nodes > 20000 || depth > 24) throw Error('PUBLIC_FIELD_STRUCTURE_BOUND');
  if (value === null || typeof value === 'boolean') return value;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    if (encoder.encode(value).byteLength > 131072) throw Error('PUBLIC_FIELD_STRING_BOUND');
    return value;
  }
  if (Array.isArray(value)) {
    if (value.length > 4096) throw Error('PUBLIC_FIELD_ARRAY_BOUND');
    return value.map(item => copyJSON(item, depth + 1, budget));
  }
  if (!value || typeof value !== 'object' ||
      ![null, Object.prototype].includes(Object.getPrototypeOf(value)))
    throw Error('PUBLIC_FIELD_JSON_REQUIRED');
  return Object.fromEntries(Object.entries(value).map(([key, item]) => {
    if (encoder.encode(key).byteLength > 4096) throw Error('PUBLIC_FIELD_KEY_BOUND');
    return [key, copyJSON(item, depth + 1, budget)];
  }));
}

export function capturePublicProduct(product) {
  if (!product || typeof product !== 'object' || Array.isArray(product) ||
      !product.fields || typeof product.fields !== 'object' || Array.isArray(product.fields))
    throw Error('PUBLIC_PRODUCT_FIELDS_REQUIRED');
  const budget = {nodes: 0}, fields = {}, fieldCapture = {};
  for (const name of PUBLIC_FIELDS) {
    if (!Object.hasOwn(product.fields, name)) {
      fieldCapture[name] = {valueCaptureState: 'not-provided-by-selected-representation'};
      continue;
    }
    const field = product.fields[name];
    fields[name] = copyJSON(field, 0, budget);
    fieldCapture[name] = {
      representationCaptured: true,
      valueCaptureState: field && typeof field === 'object' && Object.hasOwn(field, 'value')
        ? 'captured' : 'not-provided-by-selected-representation',
    };
  }
  const binding = Object.fromEntries(BINDING_KEYS.filter(key => Object.hasOwn(product, key))
    .map(key => [key, copyJSON(product[key], 0, budget)]));
  const result = {
    schema: 'offmenu-public-field-capture/1', binding, fields, fieldCapture,
    unselectedFieldCount: Object.keys(product.fields).filter(key => !PUBLIC_FIELDS.includes(key)).length,
    scope: 'Selected public projected facts; source claims remain attributed and unresolved mappings remain unresolved.',
  };
  if (encoder.encode(JSON.stringify(result)).byteLength > 262144)
    throw Error('PUBLIC_FIELD_OUTPUT_BOUND');
  return result;
}

export function capturePublicProducts(products) {
  if (!Array.isArray(products) || products.length > 25)
    throw Error('PUBLIC_PRODUCTS_BOUND');
  const result = products.map(capturePublicProduct);
  if (encoder.encode(JSON.stringify(result)).byteLength > 262144)
    throw Error('PUBLIC_PRODUCTS_OUTPUT_BOUND');
  return result;
}

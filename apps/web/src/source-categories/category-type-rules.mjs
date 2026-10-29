// Pure source-category presentation candidate. Never a product/ingredient classifier.
export function compileTypeRules({taxonomy, rules}) {
  if (!taxonomy || !rules || rules.schema !== 'offmenu-off-category-type-rules/1') throw Error('Invalid inputs');
  // Isolate the verified compile-time snapshot; callers retain ownership of their inputs.
  taxonomy = structuredClone(taxonomy);
  rules = structuredClone(rules);
  const roots = new Map();
  for (const rule of rules.foodRules) {
    if (roots.has(rule.rootID) || !Object.hasOwn(taxonomy, rule.rootID) || taxonomy[rule.rootID]?.name?.en !== rule.sourceEnglishName) throw Error('Unbound rule root');
    roots.set(rule.rootID, rule);
  }
  if (!Object.hasOwn(taxonomy, rules.nonFoodRootID)) throw Error('Missing nonfood root');
  function resolve(namespace, id) {
    const base = {schema:'offmenu-off-category-type-view/1', namespace, categoryID:id, snapshotSHA256:rules.snapshotSHA256, admission:'candidate-review-required', semanticIdentity:false, productBinding:false, type:null, icon:null, fallback:true, rootEvidence:[], issues:[]};
    if (namespace !== 'off' || typeof id !== 'string' || !Object.hasOwn(taxonomy,id)) return {...base,status:'absent-or-unsupported-namespace'};
    const found = new Map(), missing = new Set(), bad = new Set(), active = new Set(), done = new Set();
    function visit(nodeID,path) {
      if (active.has(nodeID)) { bad.add('cycle:'+nodeID); return; }
      if (!Object.hasOwn(taxonomy,nodeID)) { missing.add(nodeID); return; }
      if (done.has(nodeID)) return;
      active.add(nodeID);
      if (roots.has(nodeID) || nodeID === rules.nonFoodRootID) found.set(nodeID,[...path,nodeID]);
      const node=taxonomy[nodeID], parents=node?.parents ?? [];
      if (!Array.isArray(parents) || parents.some(p=>typeof p!=='string')) bad.add('invalid-parents:'+nodeID);
      else for (const parent of [...parents].sort()) visit(parent,[...path,nodeID]);
      active.delete(nodeID); done.add(nodeID);
    }
    visit(id,[]);
    base.rootEvidence=[...found].sort(([a],[b])=>a.localeCompare(b)).map(([rootID,path])=>({rootID,path}));
    base.issues=[...bad,...[...missing].map(p=>'missing-parent:'+p)].sort();
    if (base.issues.length) return {...base,status:'unresolved-hierarchy'};
    const food=[...found.keys()].filter(k=>roots.has(k));
    if (found.has(rules.nonFoodRootID)) return {...base,status:food.length?'ambiguous-food-nonfood':'nonfood'};
    if (food.length>1) return {...base,status:'ambiguous-types'};
    if (!food.length) return {...base,status:'unresolved-no-rule'};
    const rule=roots.get(food[0]);
    return {...base,status:'source-supported-type-candidate',type:{id:rule.typeID,label:rule.sourceEnglishName,sourceRootID:rule.rootID},icon:{path:rule.icon.path,sha256:rule.icon.sha256,rightsID:rule.icon.rightsID},fallback:false};
  }
  return Object.freeze({resolve});
}

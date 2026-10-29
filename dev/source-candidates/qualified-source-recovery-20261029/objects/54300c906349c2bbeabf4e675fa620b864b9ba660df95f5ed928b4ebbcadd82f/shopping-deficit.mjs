/** Pure DEV calculation, not a shopping-plan/duration feature or runtime hook.
 * Input: explicit {requirements: Row[], available: Row[]} (max 1,000 each).
 * Row: {rowRef, ingredientId, unit, basis, quantity}; rowRef is a caller's opaque
 * citation, retained with its original side/index even when citations repeat.
 * Identity/unit/basis strings compare EXACTLY. Missing keys are ungroupable;
 * missing/null quantities are unknown, never zero. Unknown groups have null
 * totals/deficits plus separately labelled known subtotals. Explicit available:[]
 * means no supplied compatible lots. Incompatible variants are NOT converted
 * or credited; their separate exact-key deficits remain visible, complete:false.
 * No identity inference, expiry/usability judgment, serving/density/unit/price/
 * pack calculation, duration optimisation, source admission or IO is performed.
 */
const FIELDS=new Set(['rowRef','ingredientId','unit','basis','quantity']);
function data(object,allowed){
 if(!object||typeof object!=='object'||Array.isArray(object)||![Object.prototype,null].includes(Object.getPrototypeOf(object)))throw Error('Plain input object required');
 const out=Object.create(null);
 for(const key of Reflect.ownKeys(object)){
  const d=Object.getOwnPropertyDescriptor(object,key);
  if(typeof key!=='string'||!allowed.has(key)||!d.enumerable||!Object.hasOwn(d,'value'))throw Error('Unsupported field or accessor');
  out[key]=d.value;
 }
 return out;
}
function token(value){
 if(value===null||value===undefined||value==='')return null;
 if(typeof value!=='string'||value.length>256)throw Error('Bounded opaque string required');
 return value.trim()?value:null; // whitespace-only is unknown; other values stay exact.
}
// Sum canonical decimal representations of supplied finite Numbers, without
// epsilon clamping, quantity rounding or changing units/basis. This avoids a
// spurious 0.1+0.2-0.3 deficit; output Numbers still have normal representability.
function decimal(value){
 const [mantissa,power='0']=String(value).toLowerCase().split('e');
 const [whole,fraction='']=mantissa.split('.');
 return {n:BigInt(whole+fraction),e:Number(power)-fraction.length};
}
function add(values){
 const terms=values.map(decimal);if(!terms.length)return {n:0n,e:0};
 const e=Math.min(...terms.map(t=>t.e));
 return {n:terms.reduce((sum,t)=>sum+t.n*10n**BigInt(t.e-e),0n),e};
}
function number(term){
 // Check the exact decimal aggregate before Number can round it down to a
 // finite MAX_VALUE. Preserve the reviewed algorithm and reject out-of-domain
 // totals rather than silently clamping them.
 const maximum=((1n<<53n)-1n)*(1n<<971n);
 const exceeds=term.e>=0 ? term.n*10n**BigInt(term.e)>maximum
  : term.n>maximum*10n**BigInt(-term.e);
 if(exceeds)throw RangeError('Aggregate quantity outside representable range');
 const value=Number(`${term.n}e${term.e}`);
 if(!Number.isFinite(value)||(term.n>0n&&value===0))throw RangeError('Aggregate quantity outside representable range');
 return value;
}
function deficit(need,stock){
 const e=Math.min(need.e,stock.e),n=need.n*10n**BigInt(need.e-e)-stock.n*10n**BigInt(stock.e-e);
 return n<=0n?0:number({n,e});
}
export function calculateShoppingDeficit(input){
 const root=data(input,new Set(['requirements','available']));
 if(!Array.isArray(root.requirements)||!Array.isArray(root.available)||root.requirements.length>1000||root.available.length>1000)throw Error('Explicit bounded requirements and available arrays required');
 const grouped=new Map(),ungroupable=[];
 for(const side of ['requirements','available']){
  const rows=root[side];
  for(let index=0;index<rows.length;index++){
   const descriptor=Object.getOwnPropertyDescriptor(rows,String(index));
   if(!descriptor||!Object.hasOwn(descriptor,'value'))throw Error('Dense data arrays required');
   const row=data(descriptor.value,FIELDS),rowRef=token(row.rowRef);
   if(rowRef===null)throw Error('Original rowRef required');
   const key={ingredientId:token(row.ingredientId),unit:token(row.unit),basis:token(row.basis)};
   const q=row.quantity;
   if(q!==undefined&&q!==null&&(typeof q!=='number'||!Number.isFinite(q)||q<0))throw Error('Quantity must be a finite nonnegative Number or unknown');
   const reference={side,index,rowRef},reasons=Object.keys(key).filter(k=>key[k]===null).map(k=>`${k}-unknown`);
   if(q===undefined||q===null)reasons.push('quantity-unknown');
   if(Object.values(key).some(v=>v===null)){
    ungroupable.push({groupIndex:null,key,rowReferences:[reference],quantity:q??null,reasons});continue;
   }
   const encoded=JSON.stringify([key.ingredientId,key.unit,key.basis]);
   if(!grouped.has(encoded))grouped.set(encoded,{key,requirements:[],available:[],requirementRefs:[],availableRefs:[],unknownRequirements:false,unknownAvailable:false});
   const g=grouped.get(encoded);g[side==='requirements'?'requirementRefs':'availableRefs'].push(reference);
   if(q===undefined||q===null)g[side==='requirements'?'unknownRequirements':'unknownAvailable']=true;
   else g[side].push(q);
  }
 }
 const unknownGroups=[...ungroupable],groups=[];
 for(const g of grouped.values()){
  const required=add(g.requirements),available=add(g.available),unknown=g.unknownRequirements||g.unknownAvailable;
  const result={...g.key,requirementRefs:g.requirementRefs,availableRefs:g.availableRefs,
   requiredKnownSubtotal:number(required),availableKnownSubtotal:number(available),
   requiredQuantity:g.unknownRequirements?null:number(required),availableQuantity:g.unknownAvailable?null:number(available),
   deficit:unknown?null:deficit(required,available),status:unknown?'unknown':'known'};
  if(unknown)unknownGroups.push({groupIndex:groups.length,key:{...g.key},rowReferences:[...g.requirementRefs,...g.availableRefs],reasons:[...(g.unknownRequirements?['requirement-quantity-unknown']:[]),...(g.unknownAvailable?['available-quantity-unknown']:[])]});
  groups.push(result);
 }
 const byIngredient=new Map();groups.forEach((g,index)=>{if(!byIngredient.has(g.ingredientId))byIngredient.set(g.ingredientId,[]);byIngredient.get(g.ingredientId).push(index);});
 const incompatibleGroups=[];
 for(const [ingredientId,indexes]of byIngredient)if(indexes.length>1)incompatibleGroups.push({ingredientId,groupIndexes:indexes,reason:'Exact unit/basis mismatch; no conversion or equivalence inferred',variants:indexes.map(index=>({unit:groups[index].unit,basis:groups[index].basis,requirementRefs:groups[index].requirementRefs,availableRefs:groups[index].availableRefs}))});
 return {groups,unknownGroups,incompatibleGroups,complete:!unknownGroups.length&&!incompatibleGroups.length};
}

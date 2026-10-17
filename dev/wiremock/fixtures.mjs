// All values here are synthetic. Never substitute customer data or real credentials.
const token=(id)=>'eyJhbGciOiJub25lIn0.'+Buffer.from(JSON.stringify({sub:'fixture-'+id,exp:2051222400})).toString('base64url')+'.fixture';
export const ACTORS=Object.fromEntries(['alice','bob','admin'].map(id=>[id,{id:'fixture-'+id,email:id+'@example.test',confirmed_at:'2026-01-01T00:00:00Z',email_confirmed_at:'2026-01-01T00:00:00Z',app_metadata:{roles:id==='admin'?['offmenu-admin']:[]},user_metadata:{},token:token(id),refreshToken:'fixture-refresh-'+id}]));
export const publicActor=({token,refreshToken,...actor})=>actor;
export const identityToken=(id)=>({access_token:ACTORS[id].token,token_type:'Bearer',expires_in:3600,refresh_token:ACTORS[id].refreshToken});
export const BINDINGS=()=>({PROVIDER_VAULT_KEY:'a'.repeat(64),BREVO_API_KEY:'fixture-brevo',BREVO_SENDER_EMAIL:'support@example.test',BREVO_SENDER_NAME:'OffMenu development fixture',SUPPORT_EMAIL:'support@example.test',CARE_AI_ORIGIN:'https://ai.offmenu.test',CARE_AI_KEY:'fixture-ai'});
export const PRODUCT={code:'0000000000001',status:1,status_verbose:'fixture product found',product:{code:'0000000000001',product_name:'Fixture oats',product_name_en:'Fixture oats',lang:'en',quantity:'500 g',product_quantity:500,product_quantity_unit:'g',brands:'Synthetic development fixture',ingredients_text:'Fixture oats',allergens_tags:[],countries_tags:['en:australia'],nutriments:{'energy-kcal_100g':370,proteins_100g:13},nutrition_data_per:'100g'}};
export const RESPONSES={
  off:PRODUCT,
  prices:{items:[{id:1,product_code:'0000000000001',price:2,currency:'AUD',date:'2026-01-01',location:{name:'Fixture shop',country:'AU'}}],total:1},
  usda:{foods:[{fdcId:1,description:'Fixture oats',foodNutrients:[{nutrientId:1003,nutrientName:'Protein',unitName:'G',value:13}]}]},
  edamam:{text:'Fixture oats',hints:[{food:{foodId:'fixture-oats',label:'Fixture oats',nutrients:{ENERC_KCAL:370,PROCNT:13},category:'Generic foods'}}]},
  'fsa-alerts':{items:[{id:'fixture-alert',title:'Synthetic recall exercise',description:'Not a real recall',created:'2026-01-01',notation:'fixture'}]},
  'fsa-ratings':{establishments:[{FHRSID:1,BusinessName:'Fixture kitchen',RatingValue:'5',RatingDate:'2026-01-01',LocalAuthorityName:'Fixture authority',PostCode:'FIXTURE'}]},
  fda:{results:[{recall_number:'fixture-1',product_description:'Synthetic recall exercise',reason_for_recall:'Not a real recall',status:'Ongoing',report_date:'20260101'}]},
  gleif:{data:[{id:'FIXTURE0000000000000',attributes:{lei:'FIXTURE0000000000000',entity:{legalName:{name:'Fixture food company'},legalJurisdiction:'AU',status:'ACTIVE'},registration:{initialRegistrationDate:'2026-01-01'}}}]},
  wikidata:{entities:{Q1:{id:'Q1',labels:{en:{value:'Fixture food company'}},claims:{}}}},
  brevo:{messageId:'<fixture-message@localhost>'},
  sentry:{},
  'community-ai':{action:'hold',confidence:0.5,reason:'uncertain'},
};
export const EMPTY={off:{code:'9999999999999',status:0,status_verbose:'fixture unknown barcode'},prices:{items:[],total:0},usda:{foods:[]},edamam:{text:'',hints:[]},'fsa-alerts':{items:[]},'fsa-ratings':{establishments:[]},fda:{results:[]},gleif:{data:[]},wikidata:{entities:{}}};
export const BROWSER_SCRIPTS={iubenda:'window._iub=window._iub||[];window.__tcfapi=function(c,v,cb){if(c==="addEventListener")cb({eventStatus:"tcloaded",listenerId:1,purpose:{consents:{}},vendor:{consents:{}}},true);else if(cb)cb(true);};',sleekplan:'window.$sleek=window.$sleek||[];',adsense:'window.adsbygoogle=window.adsbygoogle||[];'};

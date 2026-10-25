import {createLandingPlayback} from './landing-playback.mjs';
// The feature values below are copied byte-for-byte from the approved
// offmenu-approved-feature-copy/1 source. The build receipt pins that source.
const FEATURES = [{"key":"Barcode scanning","value":"Scan an item to find out what it is.","availability":"foundation_unverified"},{"key":"Manual entry","value":"Type a barcode when the camera cannot read it.","availability":"foundation_unverified"},{"key":"Photo scanning","value":"Find an item from a clear picture of its barcode.","availability":"foundation_unverified"},{"key":"Scanner devices","value":"Use a compatible scanner as well as your phone.","availability":"foundation_unverified"},{"key":"Product details","value":"See the information available about each product.","availability":"foundation_unverified"},{"key":"Product pictures","value":"Recognise the same item wherever you see it.","availability":"foundation_unverified"},{"key":"Loose food","value":"Add fruit, vegetables and ingredients without a barcode.","availability":"foundation_unverified"},{"key":"Home checkout","value":"Scan your shopping, review your receipt and put it away.","availability":"foundation_unverified"},{"key":"Shelf check","value":"Check what is on a shelf and update its contents.","availability":"foundation_unverified"},{"key":"Kitchen spaces","value":"Keep track of food in your pantry, fridge, freezer and other spaces.","availability":"foundation_unverified"},{"key":"Quantities","value":"Know how much you have, including partly used packs.","availability":"foundation_unverified"},{"key":"Freshness","value":"Keep label dates and check reminders close at hand.","availability":"foundation_unverified"},{"key":"Waste","value":"Record what was thrown away and where it came from.","availability":"foundation_unverified"},{"key":"Ingredient matching","value":"See how products connect to the ingredients you cook with.","availability":"foundation_unverified"},{"key":"Recipe discovery","value":"Find recipes by dish, ingredient or source.","availability":"foundation_unverified"},{"key":"Meal ideas","value":"Discover meals you can make with what you have.","availability":"foundation_unverified"},{"key":"Meal planning","value":"Plan breakfasts, lunches, dinners and snacks for your week.","availability":"foundation_unverified"},{"key":"Household portions","value":"Plan the right portions for the people eating.","availability":"foundation_unverified"},{"key":"Food preferences","value":"Keep everyone’s likes and avoided ingredients in mind.","availability":"foundation_unverified"},{"key":"Nutrition sources","value":"See where food facts come from and what is missing.","availability":"foundation_unverified"},{"key":"Cooking records","value":"Keep track of ingredients used and meals prepared.","availability":"foundation_unverified"},{"key":"Food history","value":"Look back at meals, drinks and snacks you recorded.","availability":"foundation_unverified"},{"key":"Shopping lists","value":"Turn your meal plan into a shared shopping list.","availability":"foundation_unverified"},{"key":"Price history","value":"Compare recorded prices without confusing them with today’s offers.","availability":"foundation_unverified"},{"key":"Shared kitchens","value":"Share a kitchen while choosing who can view or change it.","availability":"foundation_unverified"},{"key":"Connection recovery","value":"Keep track of unsaved changes when your connection drops.","availability":"foundation_unverified"},{"key":"Backups","value":"Keep a copy of your kitchen information.","availability":"foundation_unverified"},{"key":"Printable documents","value":"Take your recipes, receipts, menus and shopping lists with you.","availability":"foundation_unverified"},{"key":"Accessible scanning","value":"Choose controls and feedback that suit you.","availability":"foundation_unverified"},{"key":"Personal connections","value":"Connect supported services using your own accounts.","availability":"foundation_unverified"},{"key":"Connected assistants","value":"Let authorised apps help with the information you choose to share.","availability":"foundation_unverified"},{"key":"Help and corrections","value":"Tell us when product or recipe information needs attention.","availability":"foundation_unverified"},{"key":"Recipe community","value":"Share recipes while keeping their authors and sources visible.","availability":"foundation_unverified"},{"key":"Positive achievements","value":"Celebrate variety, organisation and taking part.","availability":"foundation_unverified"},{"key":"Global information","value":"Bring product knowledge from different countries into one place.","availability":"future"},{"key":"Non-food products","value":"Find out about everyday items, not just food.","availability":"future"},{"key":"Product categories","value":"See how each scanned product has been classified.","availability":"future"},{"key":"Complete details","value":"Explore the available source information beyond the summary.","availability":"future"},{"key":"English food knowledge","value":"Connect international food names through shared English terms.","availability":"future"},{"key":"Recipe steps","value":"Follow clear cooking steps with ingredients and amounts linked together.","availability":"future"},{"key":"Recipe scaling","value":"Adjust quantities for the portions you want to make.","availability":"future"},{"key":"Substitutions","value":"Review alternatives without hiding changes to nutrition or ingredients.","availability":"future"},{"key":"Recipe nutrition","value":"See nutrition for the whole recipe and each serving.","availability":"future"},{"key":"Use-first meals","value":"Find ideas that help you use food already waiting in your kitchen.","availability":"future"},{"key":"Reusable plans","value":"Adapt a favourite week for attendance, time and equipment.","availability":"future"},{"key":"Private recipes","value":"Keep family recipes and permitted bookmarks in your own collection.","availability":"future"},{"key":"Receipt capture","value":"Check and correct receipt details before adding items.","availability":"future"},{"key":"Food containers","value":"Track food you open, freeze, thaw or move into another container.","availability":"future"},{"key":"Pack sizes and budgets","value":"Plan the packs you need around your budget.","availability":"future"},{"key":"Shopping handoff","value":"Review your list before sending it to a supported service.","availability":"future"},{"key":"Brands and suppliers","value":"Explore who makes and supplies your products.","availability":"future"},{"key":"Product origins","value":"See the evidence about where products were grown, made or packed.","availability":"future"},{"key":"Dietary information","value":"Keep known restrictions and missing information clearly separate.","availability":"future"},{"key":"Certification claims","value":"Check the source behind product-specific claims.","availability":"future"},{"key":"Product recalls","value":"Review notices that may match your product, market and batch.","availability":"future"},{"key":"Restaurant menus","value":"Explore available menu and ingredient information when eating out.","availability":"future"},{"key":"Country food baskets","value":"Compare food baskets using their recorded quantities and sources.","availability":"future"},{"key":"Sign-in choices","value":"Access your account through supported sign-in options.","availability":"future"},{"key":"Profile privacy","value":"Keep personal health information separate from general household access.","availability":"future"},{"key":"Protected portability","value":"Move your records without carrying over passwords or access grants.","availability":"future"},{"key":"Care sharing","value":"Share selected dietary information with people you authorise.","availability":"future"},{"key":"Health records","value":"Keep chosen measurements alongside your food history.","availability":"future"},{"key":"Personal AI","value":"Choose what your own assistant can access and help with.","availability":"future"},{"key":"Home integrations","value":"Bring supported kitchen routines to compatible home tools.","availability":"future"},{"key":"Personal restrictions","value":"Plan meals around each person’s recorded restrictions and preferences.","availability":"future_phase_two"},{"key":"Family meals","value":"Make one meal work for different people and portions.","availability":"future_phase_two"},{"key":"Serving","value":"Record what each person was actually served.","availability":"future_phase_two"},{"key":"Consumption","value":"Record what was eaten, not just what was put on the plate.","availability":"future_phase_two"},{"key":"Uneaten components","value":"Capture which parts of a meal were left behind.","availability":"future_phase_two"},{"key":"Leftovers","value":"Put prepared food back into storage with its remaining quantity and nutrition.","availability":"future_phase_two"},{"key":"Leftover reuse","value":"Bring saved food into another meal without counting it twice.","availability":"future_phase_two"},{"key":"Individual history","value":"Follow each person’s recorded intake over time.","availability":"future_phase_two"},{"key":"Preference review","value":"Notice repeated avoidance and ask whether a preference should change.","availability":"future_phase_two"},{"key":"Intake gaps","value":"Flag recorded intake below chosen targets without treating missing logs as zero.","availability":"future_phase_two"},{"key":"Better planning","value":"Use food history, preferences and leftovers to shape the next menu.","availability":"future_phase_two"}];
const FEATURE_BY_KEY = new Map(FEATURES.map(feature => [feature.key, feature]));

const STAGES = [
  {title:'Barcode',key:'Barcode scanning',focus:'barcode',actor:39,action:'scan'},
  {title:'Product',key:'Product details',focus:'product',actor:36,action:'inspect'},
  {title:'Ingredient',key:'Ingredient matching',focus:'ingredient',actor:42,action:'prepare'},
  {title:'Recipe',key:'Recipe discovery',focus:'recipe',actor:45,action:'mix'},
  {title:'Quantity',key:'Quantities',focus:'ingredient',actor:40,action:'measure'},
  {title:'Nutrition',key:'Nutrition sources',focus:'nutrition',actor:53,action:'review'},
  {title:'Menu',key:'Meal planning',focus:'menu',actor:59,action:'plan'},
  {title:'Serving',key:'Serving',focus:'serving',actor:52,action:'serve'},
  {title:'Consumption',key:'Consumption',focus:'serving',actor:49,action:'eat'},
  {title:'Leftovers',key:'Leftovers',focus:'leftovers',actor:34,action:'store'},
  {title:'History',key:'Individual history',focus:'pantry',actor:31,action:'review'},
  {title:'Planning',key:'Better planning',focus:'planning',actor:45,action:'plan'},
  {title:'Integration',key:'Home integrations',focus:'pantry',actor:57,action:'connect'},
  {title:'Ordering',key:'Shopping handoff',focus:'product',actor:40,action:'shop'},
  {title:'Receipt',key:'Receipt capture',focus:'barcode',actor:35,action:'check'}
];

const byId=id=>document.getElementById(id);
const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)');
let stageIndex=-1,neonShell=null,featureTimer=null,featureIndex=0,neonCycles=0,springFrame=0,programmaticTarget=null;
const sections=[];
function featureText(feature){return feature.value+(feature.availability.startsWith('future')?'*':'');}
function buildChapters(){
 const host=byId('chapter-sections');
 STAGES.forEach((stage,index)=>{
  const feature=FEATURE_BY_KEY.get(stage.key),section=document.createElement('section');
  section.className='chapter snap-section';section.id='step-'+(index+1);section.dataset.index=String(index);
  section.setAttribute('aria-labelledby','chapter-title-'+(index+1));
  if(index===0){
   const eyebrow=document.createElement('p');eyebrow.className='eyebrow';eyebrow.textContent='Meet OffMenu';
   const headline=document.createElement('h1');headline.textContent='From product to pantry to plate';
   const featureLine=document.createElement('p');featureLine.id='feature-line';featureLine.className='feature-intro';featureLine.setAttribute('aria-live','off');featureLine.textContent=featureText(FEATURES[0]);
   section.append(eyebrow,headline,featureLine);
  }
  const heading=document.createElement('div');heading.className='chapter-heading';
  const circle=document.createElement('span');circle.className='chapter-number';circle.setAttribute('aria-hidden','true');circle.textContent=String(index+1).padStart(2,'0');
  const labels=document.createElement('div'),count=document.createElement('p'),title=document.createElement('h2');
  count.className='chapter-count';count.textContent='Step '+(index+1)+' of '+STAGES.length;
  title.id='chapter-title-'+(index+1);title.textContent=stage.title;labels.append(count,title);heading.append(circle,labels);
  const description=document.createElement('p');description.className='chapter-description';description.textContent=feature?featureText(feature):stage.title;
  section.append(heading,description);
  if(index===STAGES.length-1){const finalLink=document.createElement('a');finalLink.className='final-sign-in';finalLink.href='/auth.html';finalLink.textContent='Sign in or create account';section.append(finalLink);}
  host.append(section);sections.push(section);
 });
}
function updateFeatureRotation(){
 clearInterval(featureTimer);featureTimer=null;
 const line=byId('feature-line');
 if(!line||reducedMotion.matches||document.hidden)return;
 featureTimer=setInterval(()=>{
  if(document.hidden)return;
  line.classList.add('changing');
  setTimeout(()=>{
   featureIndex=(featureIndex+1)%FEATURES.length;
   line.textContent=featureText(FEATURES[featureIndex]);
   line.classList.remove('changing');
  },320);
 },6000);
}
function renderStage(index, token){
 if(index<0||index>=STAGES.length)return;
 const previous=stageIndex,stage=STAGES[index],scene=byId('scene'),actor=byId('actor-wrap');stageIndex=index;
 scene.dataset.focus=stage.focus;scene.dataset.action=stage.action;
 scene.style.setProperty('--pan-x',Math.max(-22,Math.min(22,Math.round((39-stage.actor)*1.4)))+'px');
 actor.style.left=stage.actor+'%';
 const travel=reducedMotion.matches?'0ms':Math.max(130,Math.round(440/Math.max(1,Math.abs(index-previous))))+'ms';
 scene.style.setProperty('--travel-ms',travel);actor.style.setProperty('--travel-ms',travel);
 byId('scene-caption').textContent=stage.title+' in the same kitchen.';
 dispatchEvent(new CustomEvent('offmenu:sceneSelected',{detail:{index,generation:token,source:'landing-playback'}}));
}
function chapterPosition(){
 const pages=[byId('intro'),...sections],center=innerHeight*.5;
 let nearest=0,distance=Infinity;
 pages.forEach((page,index)=>{const r=page.getBoundingClientRect(),d=Math.abs((r.top+r.bottom)/2-center);if(d<distance){distance=d;nearest=index;}});
 return nearest;
}
function cancelSpring(){if(springFrame)cancelAnimationFrame(springFrame);springFrame=0;programmaticTarget=null;}
function springScrollTo(index){
 const target=index===0?byId('intro'):sections[index-1];if(!target)return;
 cancelSpring();programmaticTarget=index;
 const from=scrollY,to=from+target.getBoundingClientRect().top,start=performance.now();
 const step=now=>{
  if(programmaticTarget!==index)return;
  const t=Math.min(1,(now-start)/760),progress=1-(1+9*t)*Math.exp(-9*t);
  scrollTo(0,from+(to-from)*(t===1?1:progress));
  if(t<1)springFrame=requestAnimationFrame(step);
  else{springFrame=0;programmaticTarget=null;}
 };
 springFrame=requestAnimationFrame(step);
}
const playback=createLandingPlayback({
 stageCount:STAGES.length+1,
 onStage(index,token){if(index>0)renderStage(index-1,token);},
 onAdvance(next){playback.select(next);springScrollTo(next);}
});
function activeChapter(){
 if(programmaticTarget!==null)return;
 const next=chapterPosition();
 if(next!==playback.state.index)playback.select(next);
}
let frame=0;
addEventListener('scroll',()=>{cancelAnimationFrame(frame);frame=requestAnimationFrame(activeChapter);},{passive:true});
addEventListener('resize',activeChapter);
function userNavigated(){playback.interrupt();cancelSpring();}
for(const event of ['wheel','touchstart','pointerdown','keydown'])addEventListener(event,userNavigated,{passive:true});
addEventListener('offmenu:animationCompleted',event=>{
 const {index,generation}=event.detail||{};
 if(Number.isInteger(index)&&Number.isInteger(generation))playback.finish(index+1,generation);
});
addEventListener('offmenu:sceneReady',()=>{
 const index=playback.state.index;
 if(index>0)playback.select(index,{force:true});
});
document.addEventListener('visibilitychange',()=>playback.setPaused(document.hidden));
async function attachApprovedNeon(){
 try{
  const response=await fetch('/offmenu-neon.html',{cache:'no-store'});if(!response.ok)throw Error('Approved neon unavailable');
  const source=await response.text();if(source.length>1100000)throw Error('Approved neon exceeds bound');
  const parsed=new DOMParser().parseFromString(source,'text/html');
  const approvedStyle=parsed.querySelector('style'),approvedSign=parsed.querySelector('svg#neon-sign');
  if(!approvedStyle||!approvedSign||!source.includes('offmenu:cycle'))throw Error('Approved neon incomplete');
  const shadow=byId('neon-host').attachShadow({mode:'open'});neonShell=document.createElement('div');neonShell.className=reducedMotion.matches?'neon-shell':'neon-shell motion';
  const scoped=document.createElement('style');scoped.textContent=approvedStyle.textContent
   .replaceAll(':root','.neon-shell').replaceAll('html,body','.neon-shell')
   .replaceAll(/\bbody\b/g,'.neon-shell').replaceAll('html.motion','.neon-shell.motion')
   .replaceAll('html.paused','.neon-shell.paused').replaceAll('html.backgrounded','.neon-shell.backgrounded')
   .replaceAll('height:100vh;height:100dvh','height:100%')+'.neon-shell{width:100%;height:100%;overflow:hidden}';
  const stage=document.createElement('div');stage.className='stage';stage.append(document.importNode(approvedSign,true));neonShell.append(stage);shadow.append(scoped,neonShell);
  const sign=neonShell.querySelector('#neon-sign'),atlas=sign.querySelector('image#glass-atlas'),encoded=atlas?.getAttribute('href');
  if(!encoded?.startsWith('data:image/jpeg;base64,')||encoded.length>1050000)throw Error('Approved neon image unavailable');
  const bytes=Uint8Array.from(atob(encoded.slice('data:image/jpeg;base64,'.length)),character=>character.charCodeAt(0));
  const atlasUrl=URL.createObjectURL(new Blob([bytes],{type:'image/jpeg'}));atlas.setAttribute('href',atlasUrl);
  addEventListener('pagehide',()=>URL.revokeObjectURL(atlasUrl),{once:true});
  const circuits=[...sign.querySelectorAll('.circuit')];sign.addEventListener('animationend',event=>{
   if(event.animationName!=='energize'||!event.target.classList.contains('circuit'))return;
   event.target.classList.add('ready');if(circuits.every(circuit=>circuit.classList.contains('ready')))neonShell.classList.add('steaming');
  });
  sign.addEventListener('animationiteration',event=>{
   if(event.animationName==='steam-rise'&&event.target.dataset.master==='true'&&++neonCycles===4)playback.finish(0,playback.state.token);
  });
  document.addEventListener('visibilitychange',()=>neonShell?.classList.toggle('backgrounded',document.hidden));
 }catch(error){console.warn('Approved neon unavailable',error?.message||'unknown');byId('neon-fallback').hidden=false;}

}
buildChapters();playback.select(0);activeChapter();updateFeatureRotation();attachApprovedNeon();
reducedMotion.addEventListener('change',()=>{playback.setReducedMotion(reducedMotion.matches);updateFeatureRotation();if(stageIndex>=0)renderStage(stageIndex,playback.state.token);});
playback.setReducedMotion(reducedMotion.matches);
document.addEventListener('visibilitychange',updateFeatureRotation);

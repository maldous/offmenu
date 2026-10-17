// Hermetic advertising only: no fetch, identity, telemetry, storage or service worker.
const links=[...document.querySelectorAll('[data-nav]')];let publicNav=null;
function markStory(id){document.querySelector('.stories').dataset.currentStory=id;const active=id==='overview'||id==='kitchen'?'kitchen':id==='planning'?(publicNav==='household'?'household':'menus'):(publicNav==='shop'?'shop':'data');for(const link of links)link.setAttribute('aria-current',link.dataset.nav===active?'page':'false');}
const observer=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting)markStory(entry.target.id);},{root:document.querySelector('.stories'),threshold:.55});
for(const section of document.querySelectorAll('.hero'))observer.observe(section);
const toggle=document.getElementById('nav-toggle'),drawer=document.getElementById('workspace-navigation'),close=document.getElementById('drawer-close'),backdrop=document.getElementById('nav-backdrop');
function publicNavigation(open){document.body.classList.toggle('nav-open',open);toggle.setAttribute('aria-expanded',String(open));toggle.setAttribute('aria-label',open?'Close navigation':'Open navigation');backdrop.hidden=!open;document.querySelector('.stories').inert=open;document.querySelector('.footer').inert=open;if(open)requestAnimationFrame(()=>close.focus({preventScroll:true}));else toggle.focus({preventScroll:true});}
toggle.onclick=()=>publicNavigation(toggle.getAttribute('aria-expanded')!=='true');close.onclick=backdrop.onclick=()=>publicNavigation(false);
for(const link of links)link.addEventListener('click',()=>{publicNav=link.dataset.nav;if(document.body.classList.contains('nav-open'))publicNavigation(false);if(link.hash)markStory(link.hash.slice(1));});
document.addEventListener('keydown',e=>{if(!document.body.classList.contains('nav-open'))return;if(e.key==='Escape'){e.preventDefault();publicNavigation(false);}if(e.key==='Tab'){const items=[...drawer.querySelectorAll('a[href],button')],i=items.indexOf(document.activeElement);e.preventDefault();items[(i+(e.shiftKey?-1:1)+items.length)%items.length].focus();}});
matchMedia('(min-width:1001px)').addEventListener('change',e=>{if(e.matches&&document.body.classList.contains('nav-open'))publicNavigation(false);});
// CSS owns wheel/touch snapping. Keys and story links target complete panes.
const storyRoot=document.querySelector('.stories'),sections=[...document.querySelectorAll('.hero')];
const reduced=matchMedia('(prefers-reduced-motion:reduce)');
let wheelBusy=false,wheelReset;
storyRoot.dataset.snapState='settled';
storyRoot.addEventListener('scroll',()=>{storyRoot.dataset.snapState='moving';},{passive:true});
storyRoot.addEventListener('scrollend',()=>{storyRoot.dataset.snapState='settled';wheelBusy=false;clearTimeout(wheelReset);});
// One vertical wheel gesture selects one complete story. Oversized copy scrolls inside its pane first.
storyRoot.addEventListener('wheel',event=>{
 if(event.ctrlKey||Math.abs(event.deltaY)<=Math.abs(event.deltaX)||Math.abs(event.deltaY)<2)return;
 const index=Math.max(0,Math.min(sections.length-1,Math.round(storyRoot.scrollTop/storyRoot.clientHeight))),section=sections[index],forward=event.deltaY>0;
 if(section.scrollHeight>section.clientHeight+2&&((forward&&section.scrollTop+section.clientHeight<section.scrollHeight-2)||(!forward&&section.scrollTop>2)))return;
 event.preventDefault();if(wheelBusy)return;const next=Math.max(0,Math.min(sections.length-1,index+(forward?1:-1)));if(next===index)return;
 wheelBusy=true;sections[next].scrollIntoView({block:'start',behavior:reduced.matches?'instant':'smooth'});wheelReset=setTimeout(()=>{wheelBusy=false;},1200);
},{passive:false});
for(const link of document.querySelectorAll('a[href^="#"]'))link.addEventListener('click',event=>{const target=document.querySelector(link.hash);if(!target)return;event.preventDefault();target.scrollIntoView({block:'start',behavior:reduced.matches?'instant':'smooth'});history.replaceState(null,'',link.hash);});
storyRoot.addEventListener('keydown',event=>{
 if(event.altKey||event.ctrlKey||event.metaKey||event.target.closest('input,select,textarea,button,a'))return;
 const keys=['ArrowDown','ArrowUp','PageDown','PageUp','Home','End'];if(!keys.includes(event.key))return;
 const current=Math.max(0,Math.min(sections.length-1,Math.round(storyRoot.scrollTop/storyRoot.clientHeight))),section=sections[current];
 const forward=['ArrowDown','PageDown','End'].includes(event.key);
 if(!['Home','End'].includes(event.key)&&section.scrollHeight>section.clientHeight+2&&((forward&&section.scrollTop+section.clientHeight<section.scrollHeight-2)||(!forward&&section.scrollTop>2))){event.preventDefault();section.scrollBy({top:(forward?1:-1)*Math.max(40,section.clientHeight*.75),behavior:reduced.matches?'instant':'smooth'});return;}
 event.preventDefault();const next=event.key==='Home'?0:event.key==='End'?sections.length-1:Math.max(0,Math.min(sections.length-1,current+(forward?1:-1)));
 sections[next].scrollIntoView({block:'start',behavior:reduced.matches?'instant':'smooth'});
});

(()=>{
 const key='offmenu-scanner-theme';
 const system=matchMedia('(prefers-color-scheme: dark)');
 const root=document.documentElement;
 function read(){
  try{return localStorage.getItem(key);}catch{return null;}
 }
 function apply(theme,source){
  root.dataset.theme=theme;
  root.dataset.themeSource=source;
  for(const button of document.querySelectorAll('[data-theme-toggle]'))
   button.setAttribute('aria-pressed',String(theme==='dark'));
  const chromeColor=document.querySelector('meta[name="theme-color"]');
  if(chromeColor)chromeColor.content=theme==='dark'?'#081413':'#214638';
 }
 const preference=read();
 const retained=preference==='dark'||preference==='light';
 apply(retained?preference:system.matches?'dark':'light',retained?'persisted':'system');
 document.addEventListener('DOMContentLoaded',()=>{
  const controls=document.querySelectorAll('[data-theme-toggle]');
  if(!controls.length)return;
  apply(root.dataset.theme,root.dataset.themeSource);
  for(const button of controls)button.addEventListener('click',()=>{
   const theme=root.dataset.theme==='dark'?'light':'dark';
   try{localStorage.setItem(key,theme);}catch{}
   apply(theme,'manual');
  });
  system.addEventListener('change',event=>{
   if(root.dataset.themeSource==='system')apply(event.matches?'dark':'light','system');
  });
 });
})();

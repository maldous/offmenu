// The index is drawn from visible, bundled instructions only. No account, storage or network API.
const norm = value => String(value).normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
const ignore = new Set('a an and are can do for how i in is me my of on or the to what where'.split(' '));
export function rankedTopics(articles, query) {
  const phrase = norm(String(query).slice(0,160));
  if (!phrase) return [];
  const tokens = [...new Set(phrase.split(' ').filter(w => !ignore.has(w)))];
  if (!tokens.length) return [];
  const matches = [];
  for (const [order, topic] of articles.entries()) {
    const title = norm(topic.title), aliases = topic.aliases.map(norm), summary = norm(topic.summary), body = norm(topic.body);
    const groups = [title, aliases.join(' '), summary, body].map(v=>new Set(v.split(' ')));
    let score = aliases.includes(phrase) || title === phrase ? 100 : 0;
    for (const token of tokens) {
      const i = groups.findIndex(words=>words.has(token));
      if (i < 0) { score=-1; break; }
      score += [9,6,3,1][i];
    }
    if(score>0) matches.push({topic,score,order});
  }
  return matches.sort((a,b)=>b.score-a.score || a.order-b.order).map(r=>r.topic);
}
export function mountHelp(d=globalThis.document,w=globalThis.window) {
  const list = d.querySelector('#matches'), status = d.querySelector('#feedback'), finder=d.querySelector('#finder'),
    query=d.querySelector('#query'), back=d.querySelector('#back'), clear=d.querySelector('#clear'), body=d.querySelector('#topics');
  const elements = Array.from(body.querySelectorAll('article'));
  const articles=elements.map(el=>({id:el.id,el,title:el.querySelector('h2')?.textContent,summary:el.querySelector('p')?.textContent,body:el.textContent,aliases:(el.dataset.alias||'').split(';')}));
  if(!articles.length || new Set(articles.map(t=>t.id)).size!==articles.length ||
      articles.some(t=>!t.title || !t.summary || !/^[a-z][a-z0-9-]+$/.test(t.id))) {
    status.textContent='Help search is unavailable. Read the instructions below, or reload the page to try again.';
    return;
  }
  const getId=()=>w.location.hash.slice(1);
  let previouslyOpened=null;
  function showListing({focus=false,unknown=false}={}) {
    const words=query.value.trim(), topics=words ? rankedTopics(articles,words) : articles;
    body.hidden=true; back.hidden=true;list.hidden=false;list.replaceChildren();
    const ul=d.createElement('ul');
    for(const t of topics){
      const li=d.createElement('li'),link=d.createElement('a'),p=d.createElement('p');
      link.href='#'+t.id;link.textContent=t.title;p.textContent=t.summary;li.append(link,p);ul.append(li);
    }
    list.append(ul);status.textContent=unknown?'That help topic is unavailable. Browse the topics or search again.':
        !words?'Browse all '+topics.length+' topics, or enter a search.':
        !topics.length?'No matching help topics. Try “backup” or “restore”, or clear the search.':
        topics.length+' matching help topic'+(topics.length===1?'.':'s.');
    if(focus)(Array.from(list.querySelectorAll('a')).find(a=>a.hash==='#'+previouslyOpened)||query).focus();
  }
  function route(focus){
    const id=getId(), topic=articles.find(t=>t.id===id);
    if(id==='matches'){showListing();if(focus)list.focus();return;}
    if(!topic){const unknown=!!id&&id!=='topics';if(unknown){query.value='';previouslyOpened=null;}showListing({focus,unknown});return;}
    previouslyOpened=id;list.hidden=true;back.hidden=false;body.hidden=false;
    for(const t of articles)t.el.hidden=t!==topic;
    status.textContent='Help topic: '+topic.title+'.';if(focus)topic.el.querySelector('h2').focus();
  }
  function search(){
    if(getId())w.history.replaceState(null,'',w.location.pathname);
    previouslyOpened=null;showListing();
  }
  query.addEventListener('input',search);
  clear.addEventListener('click',()=>{query.value='';search();query.focus();});
  // Native anchors support copying and reload; search words never enter history or the URL.
  w.addEventListener('hashchange',()=>route(true));
  d.querySelector('a.skip[href="#topics"]')?.setAttribute('href','#matches');
  finder.hidden=false;route(false);
  const initialId=getId(), initialTopic=articles.find(topic=>topic.id===initialId);
  const navigation=w.performance?.getEntriesByType?.('navigation')?.[0];
  // Let the browser finish its initial fragment navigation first. Never change
  // the restored focus of a history/reload visit or interrupt an input action.
  if(initialTopic&&navigation?.type==='navigate'){
    let intervened=false;
    for(const event of ['input','keydown','pointerdown','hashchange'])
      w.addEventListener(event,()=>{intervened=true;},{once:true,capture:true});
    const afterLoad=()=>w.requestAnimationFrame(()=>w.requestAnimationFrame(()=>{
      if(!intervened&&getId()===initialId&&(d.activeElement===d.body||d.activeElement===initialTopic.el))
        initialTopic.el.querySelector('h2').focus({preventScroll:true});
    }));
    if(d.readyState==='complete')afterLoad();else w.addEventListener('load',afterLoad,{once:true});
  }
}
if(typeof document!=='undefined')mountHelp();

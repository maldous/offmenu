// Off-live UI adapter for offmenu-source-field-page/1. Host qualification,
// source access and cursor verification belong to the injected reader.
export const SOURCE_FIELD_PAGE_PRESENTER = 'offmenu-source-field-page-presenter/1';
const STATES = new Set(['present', 'null', 'missing', 'unknown', 'not-loaded', 'rights-held']);
const NONVALUE = {
  null:'Explicit source null; not zero or false', missing:'Field missing in selected source scope',
  unknown:'Source value unknown', 'not-loaded':'Source field not loaded',
  'rights-held':'Rights held; source value withheld',
};
const own = (x,k) => Object.prototype.hasOwnProperty.call(x,k);
const isObject = x => x !== null && typeof x === 'object' && !Array.isArray(x);
function canonical(x) {
  if (Array.isArray(x)) return '[' + x.map(canonical).join(',') + ']';
  if (isObject(x)) return '{' + Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+canonical(x[k])).join(',') + '}';
  return JSON.stringify(x);
}
function el(doc,tag,text) {const n=doc.createElement(tag);if(text!==undefined)n.textContent=String(text);return n;}
function row(doc,host,label,value) {const p=el(doc,'p');p.append(el(doc,'strong',label+': '),el(doc,'span',value));host.append(p);}
function validPage(page, binding, snapshot, path, cursor, expectedOffset) {
  if (!isObject(page) || page.schema!=='offmenu-source-field-page/1' ||
      page.scope!=='node-page-only' || !STATES.has(page.state) ||
      canonical(page.binding)!==canonical(binding) ||
      typeof page.snapshotSha256!=='string' ||
      snapshot!==null && page.snapshotSha256!==snapshot ||
      canonical(page.path)!==canonical(path) || page.requestCursor!==cursor ||
      typeof page.nodeExhausted!=='boolean' || typeof page.valueCompleteInThisPage!=='boolean' ||
      !(page.nextCursor===null || typeof page.nextCursor==='string' && page.nextCursor.length>0) ||
      page.nodeExhausted!== (page.nextCursor===null)) throw Error('Field page binding mismatch');
  if (page.state!=='present') {
    if (page.content!==null || !page.nodeExhausted) throw Error('Field page state mismatch');
    return;
  }
  const c=page.content;
  if (!isObject(c) || !['text','object','array','number','boolean','null'].includes(c.kind))
    throw Error('Field page kind unavailable');
  if (c.kind==='text') {
    if (typeof c.text!=='string' || c.offsetUnit!=='unicode-code-points' ||
        !Number.isSafeInteger(c.start) || c.start!==expectedOffset ||
        !Number.isSafeInteger(c.end) || c.end!==c.start+Array.from(c.text).length ||
        !Number.isSafeInteger(c.total) || c.end>c.total ||
        page.nodeExhausted!==(c.end===c.total)) throw Error('Field text page gap');
  } else if (c.kind==='object' || c.kind==='array') {
    if (!Array.isArray(c.children) || !Number.isSafeInteger(c.start) || c.start!==expectedOffset ||
        !Number.isSafeInteger(c.end) || c.end!==c.start+c.children.length ||
        !Number.isSafeInteger(c.total) || c.end>c.total ||
        page.nodeExhausted!==(c.end===c.total) ||
        c.children.some(child=>!isObject(child) ||
          !(c.kind==='array' ? Number.isSafeInteger(child.key) : typeof child.key==='string') ||
          typeof child.cursor!=='string' || !child.cursor)) throw Error('Field container page gap');
  } else if (expectedOffset!==0 || !page.nodeExhausted) throw Error('Field scalar continuation');
  if (c.kind==='number' && (typeof c.jsonNumber!=='string' ||
      !/^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?$/.test(c.jsonNumber)))
    throw Error('Field number unavailable');
}
/** readPage({binding,opaqueCursor,generation}) is already qualified and read-only. */
export function mountSourceFieldPagePresenter(root,{readPage,generation=null}={}) {
  if (!root?.ownerDocument?.createElement || typeof readPage!=='function') throw new TypeError('Reader and root required');
  const doc=root.ownerDocument;
  let epoch=0, binding=null, snapshot=null, rootNode=null, summary=null;
  const nodes=new Map();
  function key(path) {return canonical(path);}
  function complete(node) {
    if (!node || !node.exhausted) return false;
    if (node.stateCode==='null') return node.valueComplete===true;
    if (node.stateCode!=='present') return false;
    if (node.kind==='text') return node.offset===node.total;
    if (node.kind==='object' || node.kind==='array')
      return node.offset===node.total && [...node.children.values()].every(complete);
    return true;
  }
  function refresh() {
    summary.textContent=complete(rootNode) ?
      'Selected field traversal complete. Other source fields and global coverage are not established.' :
      'Selected field traversal incomplete; unloaded children or continuations remain.';
  }
  function makeNode(path,label) {
    const section=el(doc,'section');section.append(el(doc,'h4',label));
    const state=el(doc,'p','Awaiting source field page');section.append(state);
    const values=el(doc,'div');section.append(values);
    const children=el(doc,'div');section.append(children);
    const more=el(doc,'button','Load next field page');more.type='button';more.hidden=true;section.append(more);
    const node={path,section,state,values,childHost:children,more,children:new Map(),
      offset:0,total:null,nextCursor:null,exhausted:false,kind:null,pending:false};
    nodes.set(key(path),node);
    more.onclick=()=>{void load(node,node.nextCursor);};
    return node;
  }
  function apply(node,page) {
    const c=page.content;
    node.state.textContent=page.state==='present' ?
      'Source field value supplied · node page only' : NONVALUE[page.state];
    node.stateCode=page.state;
    if (page.state==='present') {
      node.kind=c.kind;
      if (c.kind==='text') {row(doc,node.values,'Source text',c.text);node.offset=c.end;node.total=c.total;}
      else if (c.kind==='object'||c.kind==='array') {
        for (const child of c.children) {
          const childPath=[...node.path,child.key], id=key(childPath);
          if (nodes.has(id)) throw Error('Repeated source child');
          const childNode=makeNode(childPath,String(child.key)+' · '+String(child.valueType));
          node.children.set(id,childNode);
          const open=el(doc,'button','Load child '+String(child.key));open.type='button';
          open.onclick=()=>{open.disabled=true;void load(childNode,child.cursor).then(ok=>{if(ok)open.hidden=true;}).finally(()=>{open.disabled=false;});};
          node.childHost.append(open,childNode.section);
        }
        node.offset=c.end;node.total=c.total;
      } else {
        row(doc,node.values,'Source value',c.kind==='number'?c.jsonNumber:
          c.kind==='null'?'null':String(c.value));
      }
    }
    node.exhausted=page.nodeExhausted;node.valueComplete=page.valueCompleteInThisPage;node.nextCursor=page.nextCursor;
    node.more.hidden=node.exhausted || page.state!=='present';
    refresh();
  }
  async function load(node,cursor) {
    if (!binding || node.pending || node.exhausted || cursor===null) return false;
    const token=epoch;node.pending=true;
    try {
      const page=await readPage({binding,opaqueCursor:cursor,generation});
      if (token!==epoch) return false;
      if (page?.schema==='offmenu-source-field-page/1' && page.state==='unavailable')
        throw Error('Typed field reader failure: '+String(page.reasonCode||'unavailable'));
      validPage(page,binding,snapshot,node.path,cursor,node.offset);
      if (snapshot===null) snapshot=page.snapshotSha256;
      apply(node,page);return true;
    } catch (error) {
      if (token===epoch) {
        node.state.textContent='Field page unavailable or changed source; already loaded values remain. '+
          (error?.message||'Unknown reader error');
        refresh();
      }
      return false;
    } finally {if(token===epoch)node.pending=false;}
  }
  function show(firstPage) {
    epoch++;nodes.clear();snapshot=null;
    if (!isObject(firstPage?.binding) ||
        firstPage.binding.sourceObservationReference?.schema!=='offmenu-identifier-observation/2' ||
        typeof firstPage.binding.revisionSha256!=='string' ||
        typeof firstPage.binding.fieldPath!=='string') throw new TypeError('Exact selected field binding required');
    binding=firstPage.binding;root.replaceChildren();
    root.append(el(doc,'h3','Selected source field · '+binding.fieldPath));
    summary=el(doc,'p','Selected field traversal incomplete');root.append(summary);
    const metadata=el(doc,'details');metadata.append(el(doc,'summary','Source field attribution and metadata'));
    row(doc,metadata,'Field path',binding.fieldPath);
    row(doc,metadata,'Revision',binding.revisionSha256);
    row(doc,metadata,'Attribution',canonical(binding.attribution));
    row(doc,metadata,'Field metadata',canonical(firstPage.field));
    root.append(metadata);
    rootNode=makeNode([],'Selected field root');root.append(rootNode.section);
    try {validPage(firstPage,binding,null,[],null,0);snapshot=firstPage.snapshotSha256;apply(rootNode,firstPage);}
    catch(error) {rootNode.state.textContent='Field page unavailable: '+error.message;refresh();}
  }
  function destroy(){epoch++;binding=null;nodes.clear();root.replaceChildren();}
  return Object.freeze({show,destroy,loadNext:()=>rootNode&&load(rootNode,rootNode.nextCursor),isComplete:()=>complete(rootNode)});
}

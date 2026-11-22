// Local authoring may inject this exact inert-at-build script block.
// Never include the offending text or script source in a build error.
const MARKER=/<!--\s*impeccable-live-(start|end)\s*-->/gi;
const LOCAL_BRIDGE_SCRIPT=/^\s*<script\s+src=(["'])https?:\/\/(?:localhost|127\.0\.0\.1|\[::1\]):[1-9]\d{0,4}\/live\.js(?:\?[^"'<> \t\r\n]*)?\1\s*>\s*<\/script\s*>\s*$/i;
const AUTHORING=/impeccable[-_](?:live|variants?)|data-impeccable(?:\b|[-_])|(?:localhost|127(?:\.\d{1,3}){3}|\[::1\])(?::\d{1,5})?\\?\/live\.js\b/i;

export function assertNoPublicAuthoring(text) {
  if (typeof text!=='string'||AUTHORING.test(text)) throw new Error('Public build contains private authoring material.');
}

export function publicHTML(text) {
  if (typeof text!=='string') throw new Error('Public HTML must be text.');
  let start=null, cursor=0, result='';
  for (const match of text.matchAll(MARKER)) {
    const edge=match.index+match[0].length;
    if (match[1].toLowerCase()==='start') {
      if (start!==null) throw new Error('Invalid private authoring block.');
      result+=text.slice(cursor,match.index);
      start=edge;
    } else {
      // Reject rather than silently discard arbitrary content between markers.
      if (start===null||!LOCAL_BRIDGE_SCRIPT.test(text.slice(start,match.index))) throw new Error('Invalid private authoring block.');
      start=null;
      cursor=edge;
    }
  }
  if (start!==null) throw new Error('Invalid private authoring block.');
  result+=text.slice(cursor);
  assertNoPublicAuthoring(result);
  return result;
}

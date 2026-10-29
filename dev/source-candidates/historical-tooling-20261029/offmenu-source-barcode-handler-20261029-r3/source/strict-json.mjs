// Bounded JSON parser: JSON.parse alone discards duplicate keys before validation.
export function strictJSON(text, check = () => {}, maxNodes = 200000) {
  let i = 0, nodes = 0;
  const need = ok => { if (!ok) throw Error('invalid-json'); };
  const ws = () => { while (i < text.length && /[\t\r\n ]/.test(text[i])) i++; };
  function string() {
    const start = i++; let escaped = false;
    while (i < text.length) {
      const c = text[i++];
      if (c === '"' && !escaped) {
        const value = JSON.parse(text.slice(start,i));
        for (const cp of value) need(!(cp.codePointAt(0) >= 0xd800 && cp.codePointAt(0) <= 0xdfff));
        return value;
      }
      if (c === '\\' && !escaped) escaped = true; else escaped = false;
    }
    throw Error('unterminated-json-string');
  }
  function value(depth) {
    need(depth <= 32 && ++nodes <= maxNodes); if ((nodes & 1023) === 0) check(); ws();
    const c = text[i];
    if (c === '"') return string();
    if (c === '{' || c === '[') {
      const object = c === '{', out = object ? Object.create(null) : [];
      const keys = new Set(), close = object ? '}' : ']'; i++; ws();
      if (text[i] === close) { i++; return out; }
      while (true) {
        ws(); let key;
        if (object) { need(text[i] === '"'); key = string(); need(!keys.has(key)); keys.add(key); ws(); need(text[i++] === ':'); }
        const v = value(depth+1); if (object) out[key] = v; else out.push(v);
        ws(); const end = text[i++]; if (end === close) return out; need(end === ',');
      }
    }
    for (const [literal, result] of [['true',true],['false',false],['null',null]])
      if (text.startsWith(literal,i)) { i += literal.length; return result; }
    const match = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(text.slice(i));
    need(match); i += match[0].length; const n = Number(match[0]);
    need(Number.isFinite(n) && (!Number.isInteger(n) || Number.isSafeInteger(n))); return n;
  }
  const result = value(0); ws(); need(i === text.length); check(); return result;
}

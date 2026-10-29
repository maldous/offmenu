// Existing application D1 binding, code-only. No account/token/credential rows.
export const GOOGLE_RETURN_SQL=Object.freeze({
  cleanup:'DELETE FROM offmenu_google_return_v2 WHERE expires_at_ms<=?',
  reserve:'INSERT INTO offmenu_google_return_v2(nonce_hash,expires_at_ms) SELECT ?,? WHERE (SELECT COUNT(*) FROM offmenu_google_return_v2)<64 ON CONFLICT(nonce_hash) DO NOTHING RETURNING nonce_hash',
  consume:'DELETE FROM offmenu_google_return_v2 WHERE nonce_hash=? AND expires_at_ms>? RETURNING nonce_hash'
});
export function createD1GoogleReturnStore(DB){
  if(typeof DB?.prepare!=='function')throw Error('EXISTING_APPLICATION_DB_REQUIRED');
  return Object.freeze({async reserve(key,expires,now){
    if(!/^[a-f0-9]{64}$/.test(key)||!Number.isSafeInteger(expires)||!Number.isSafeInteger(now)||expires<=now||expires>now+300000)throw Error('RETURN_BOUNDS');
    await DB.prepare(GOOGLE_RETURN_SQL.cleanup).bind(now).run();
    const row=await DB.prepare(GOOGLE_RETURN_SQL.reserve).bind(key,expires).first();return row?.nonce_hash===key;
  },async consume(key,now){
    if(!/^[a-f0-9]{64}$/.test(key)||!Number.isSafeInteger(now))throw Error('RETURN_BOUNDS');
    const row=await DB.prepare(GOOGLE_RETURN_SQL.consume).bind(key,now).first();return row?.nonce_hash===key;
  }});
}

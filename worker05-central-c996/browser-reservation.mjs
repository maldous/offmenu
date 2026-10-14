import assert from 'node:assert/strict';
export const browser58Thread='01a139aa-f2c2-73b0-b45f-cbbafe2e326c';
export function verifyBrowserReservation(r,p,consumerThread){
 assert.equal(consumerThread,browser58Thread,'exclusive native58 consumer');assert.equal(r.schema,'offmenu-worker05-browser58-reservation/1');assert.equal(r.exclusive,true);assert.equal(r.consumerThread,browser58Thread);assert.equal(r.rootSourceThread,'01a137cf-2242-761d-8fd7-6e6fc5658013');
 assert.deepEqual(r.actors,['alice','bob','admin']);assert.deepEqual(r.permittedJourneys,['password-account-isolation-logout','care','community','admin']);assert.equal(r.selection.app,'c996bb469621c57820007c261585aba5faddd519');assert.equal(r.selection.mock,'be166bb61483825498094d496e2caed9d8b775bb');
 assert.equal(r.app.port,18818);assert.equal(r.mock.port,19088);assert.equal(p.app.port,r.app.port);assert.equal(p.mock.port,r.mock.port);assert.equal(p.app.pid,r.app.pid);assert.equal(p.mock.pid,r.mock.pid);assert.deepEqual(p.app.birth,r.app.birth);assert.deepEqual(p.mock.birth,r.mock.birth);assert.equal(p.app.runId,r.app.runId);assert.equal(p.app.statePath,r.app.statePath);assert.deepEqual(p.app.receipt,r.app.receipt);assert.deepEqual(p.descriptor,r.descriptor);assert.deepEqual(p.artifact,r.artifact);assert.deepEqual(p.mock.qualification,r.mock.qualification);assert.deepEqual(p.mock.execution,r.mock.execution);
 assert.equal(r.status,'RESERVED_PENDING_12_ADMISSION');return true;
}

// Identity owns OAuth; forward its browser callback to the fixed application origin.
// Tokens remain in the fragment and are consumed by handleAuthCallback there.
const fragment=window.location.hash;
window.history.replaceState(null,'',window.location.pathname);
window.location.replace('https://offmenu.aldous.info/'+fragment);

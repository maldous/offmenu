import {t,setLocalizedText,setupLanguage} from '../web/src/i18n.js';
import {extractRetailerRecords} from './extract.js';

setupLanguage();
const $ = id => document.getElementById(id);
let records = [];
let generation = 0;

function clearReview() {
  records = [];
  $('review').replaceChildren();
  $('confirm').checked = false;
  $('confirm').disabled = true;
  $('download').disabled = true;
}

function showRecords(items) {
  for (const r of items) {
    const card = document.createElement('article');
    const title = document.createElement('strong');
    const p = document.createElement('p');
    setLocalizedText(title,r.data.name);
    setLocalizedText(p,r.kind==='priceObservation'
      ? (r.data.currency||'Currency unknown')+' '+r.data.amount+' · '+r.data.availability
      : r.data.identifiers.map(i=>i.system+': '+i.value).join(' · '));
    card.append(title,p);
    $('review').append(card);
  }
}

clearReview();
$('read').onclick = async () => {
  const current = ++generation;
  clearReview();
  $('status').textContent = '';
  try {
    const [tab] = await chrome.tabs.query({active:true,currentWindow:true});
    if (current !== generation) return;
    const [{result}] = await chrome.scripting.executeScript({
      target:{tabId:tab.id},
      func:()=>({url:location.origin+location.pathname,blocks:[...document.querySelectorAll('script[type="application/ld+json"]')].slice(0,100).map(s=>s.textContent.slice(0,100000))}),
    });
    if (current !== generation) return;
    const items = extractRetailerRecords(result.blocks,{url:result.url});
    showRecords(items);
    // Commit only after rendering succeeds: a partial, failed review is never exportable.
    records = items;
    $('confirm').checked = false;
    $('confirm').disabled = !records.length;
    setLocalizedText($('status'),records.length
      ? t("{v0} records extracted. Verify them against the visible page.",{v0:records.length})
      : t('No supported structured product data found. Use a retailer file / receipt or enter it manually.'));
  } catch {
    if (current !== generation) return;
    clearReview();
    setLocalizedText($('status'),'Unable to read this page. Choose a retailer HTTPS product page and try again.');
  }
};

$('confirm').onchange = () => {
  $('download').disabled = !records.length || !$('confirm').checked;
};

$('download').onclick = () => {
  if (!records.length || !$('confirm').checked) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify({schemaVersion:'1.0',records},null,2)],{type:'application/json'}));
  const a = document.createElement('a');
  a.href = url;
  a.download = 'offmenu-retailer-import.json';
  a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
};

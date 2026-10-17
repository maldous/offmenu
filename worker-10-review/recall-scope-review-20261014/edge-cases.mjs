import {writeFile} from 'node:fs/promises';
import {evaluateRecallScope} from './snapshot/public/recall-scope-model.js';
const asOf='2026-10-14T06:00:00Z';
const baseNotice=()=>({id:'reviewer-notice',action:{type:'recall',regulator:'reviewer-regulator'},provenance:{sourceId:'reviewer-source',recordId:'reviewer-record',url:'https://source.invalid/notice',retrievedAt:'2026-10-14T05:00:00Z'},evidence:{kind:'current',validFrom:'2026-10-13T00:00:00Z',freshUntil:'2026-10-15T00:00:00Z'},scope:{gtin:'4006381333931',markets:['AU'],lots:['A'],labelVersions:['v1'],dateRange:{field:'bestBefore',from:'2026-10-01',through:'2026-10-31'}}});
const baseLot=()=>({barcode:'04006381333931',market:'AU',lotCode:'A',labelVersion:'v1',bestBefore:'2026-10-14'});
const observations=[];
function probe(id,mutate,expected,clock=asOf){const n=baseNotice(),l=baseLot();mutate(n,l);const before=JSON.stringify({n,l});const result=evaluateRecallScope(n,l,{asOf:clock});const unchanged=JSON.stringify({n,l})===before;observations.push({id,expected,actual:result.applicability,passed:result.applicability===expected&&unchanged&&result.automaticSelection===false,inputNotice:n,inputLot:l,asOf:clock,result,inputUnchanged:unchanged});}
probe('baseline',()=>{},'matched');
for(const [id,value] of [['ascii-space',' A'],['trailing-space','A '],['zero-width','A\u200b'],['fullwidth','Ａ'],['cyrillic-lookalike','А'],['null-control','A\u0000'],['case','a']])probe('lot-exact-'+id,(_,l)=>l.lotCode=value,'not-matched');
probe('unicode-precomposed-versus-decomposed',(n,l)=>{n.scope.lots=['é'];l.lotCode='e\u0301';},'not-matched');
probe('unicode-identical-opaque-lot',(n,l)=>{n.scope.lots=['日本ロット-２'];l.lotCode='日本ロット-２';},'matched');
probe('unicode-market-lookalike',(_,l)=>l.market='ＡＵ','not-matched');
probe('unicode-label-lookalike',(_,l)=>l.labelVersion='v１','not-matched');
probe('unicode-fullwidth-gtin',(_,l)=>l.barcode='４００６３８１３３３９３１','unknown');
probe('unicode-arabic-indic-gtin',(_,l)=>l.barcode='٤٠٠٦٣٨١٣٣٣٩٣١','unknown');
probe('gtin-zero-width',(_,l)=>l.barcode='4006381333931\u200b','unknown');
probe('missing-market-with-all-batches',(n,l)=>{delete n.scope.lots;n.scope.allBatches=true;delete l.market;},'unknown');
probe('contradictory-batch-scope',n=>n.scope.allBatches=true,'unknown');
probe('null-label-restriction',n=>n.scope.labelVersions=null,'unknown');
probe('date-equal-inclusive-through',(_,l)=>l.bestBefore='2026-10-31','matched');
probe('date-wrong-type-only',(_,l)=>{delete l.bestBefore;l.useBy='2026-10-14';},'unknown');
probe('date-outside-with-unresolved-lot',(_,l)=>{delete l.lotCode;l.bestBefore='2026-11-01';},'not-matched');
probe('date-non-leap-day',(n,l)=>{n.scope.dateRange={field:'bestBefore',from:'2026-02-01',through:'2026-03-01'};l.bestBefore='2026-02-29';},'unknown');
probe('date-reversed-range',n=>n.scope.dateRange={field:'bestBefore',from:'2026-11-01',through:'2026-10-01'},'unknown');
probe('valid-until-equals-valid-from',n=>n.evidence.validUntil=n.evidence.validFrom,'unknown');
probe('fresh-until-before-retrieval',n=>n.evidence.freshUntil='2026-10-14T04:59:59Z','unknown');
probe('effective-date-after-retrieval',n=>n.evidence.validFrom='2026-10-14T05:00:01Z','unknown');
probe('retrieval-after-asof',n=>n.provenance.retrievedAt='2026-10-14T06:00:01Z','unknown');
probe('history-despite-current-looking-dates',n=>n.evidence.kind='historical','unknown');
probe('absent-evidence',n=>delete n.evidence,'unknown');
probe('inspection-despite-current-lifecycle',n=>n.action.type='inspection','unknown');
probe('non-recall-regulatory-action',n=>n.action.type='noncompliance','unknown');
probe('missing-source-record',n=>delete n.provenance.recordId,'unknown');
probe('missing-declared-regulator',n=>delete n.action.regulator,'unknown');
// The public instant syntax admits arbitrary fractional precision; admission must not collapse ordering.
probe('submillisecond-effective-after-asof-and-retrieval',n=>{n.evidence.validFrom='2026-10-14T06:00:00.0009Z';n.provenance.retrievedAt='2026-10-14T06:00:00.0001Z';},'unknown','2026-10-14T06:00:00.0005Z');
probe('submillisecond-retrieval-in-future',n=>n.provenance.retrievedAt='2026-10-14T06:00:00.0009Z','unknown','2026-10-14T06:00:00.0001Z');
probe('submillisecond-freshness-before-actual-expiry',n=>{n.evidence.freshUntil='2026-10-14T06:00:00.0009Z';},'matched','2026-10-14T06:00:00.0001Z');
probe('milliseconds-supported-ordering',n=>n.provenance.retrievedAt='2026-10-14T06:00:00.009Z','unknown','2026-10-14T06:00:00.001Z');
// These are integration precondition probes, not conformance expectations: caller must resolve them.
const integration=[];
for(const [id,mutate] of [
 ['withdrawn-flag-outside-projection-schema',n=>n.evidence.status='withdrawn'],
 ['contradictory-action-original-text',n=>n.action.originalText='Synthetic original says inspection, not recall'],
 ['source-regulator-disagreement',n=>{n.provenance.regulator='synthetic-regulator-B';n.action.regulator='synthetic-regulator-A';}],
 ['conflicting-top-level-date',n=>n.validUntil='2026-10-12T00:00:00Z'],
 ['non-url-provenance-text',n=>n.provenance.url='synthetic-not-a-url'],
]){const n=baseNotice();mutate(n);integration.push({id,inputNotice:n,result:evaluateRecallScope(n,baseLot(),{asOf}),qualification:'Unsupported/raw/conflicting fields must be resolved by Dataset01 owner projection/admission before model call; not claimed as a recognized input field.'});}
const report={schema:'offmenu.worker10.recall-scope-edges/1',candidate:'adf42e947b21c2d5441fcb69b683c931d726e31c',cases:observations.length,passed:observations.filter(x=>x.passed).length,failed:observations.filter(x=>!x.passed).length,observations,integrationPreconditionProbes:integration};
await writeFile(new URL('./edge-results.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({cases:report.cases,passed:report.passed,failed:report.failed,failedCases:observations.filter(x=>!x.passed).map(({id,expected,actual,result})=>({id,expected,actual,result}))},null,2));
process.exitCode=report.failed?1:0;

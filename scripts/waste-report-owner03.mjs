#!/usr/bin/env node
import {createReadStream} from 'node:fs';
import {analyzeWaste} from '../public/waste-analysis-model.js';

const usage='Usage: node scripts/waste-report-owner03.mjs --account ACCOUNT [--input FILE|-] [--json]\nReads an owner-adapted JSON array from stdin by default (maximum 2 MiB, 1000 records).\nAccount selection is a scope check, not authentication. No unit/currency conversion.';
const MAX_BYTES=2*1024*1024;
function options(args){
 const out={input:'-',json:false},seen=new Set();
 for(let i=0;i<args.length;i++){
  const flag=args[i];if(!['--account','--input','--json','--help'].includes(flag)||seen.has(flag))throw Error('Unknown or repeated option: '+JSON.stringify(flag));seen.add(flag);
  if(flag==='--json')out.json=true;
  else if(flag==='--help')out.help=true;
  else {const value=args[++i];if(value===undefined||value.startsWith('--'))throw Error('Missing value for '+flag);out[flag.slice(2)]=value;}
 }
 if(!out.help&&!(typeof out.account==='string'&&out.account.trim()))throw Error('Explicit --account required.');
 return out;
}
async function readJSON(stream){
 let size=0;const chunks=[];
 for await(const chunk of stream){size+=chunk.length;if(size>MAX_BYTES)throw Error('Input exceeds 2 MiB limit.');chunks.push(chunk);}
 try{return JSON.parse(Buffer.concat(chunks).toString('utf8'));}catch{throw Error('Input must be valid JSON.');}
}
const quoted=value=>JSON.stringify(value);
function human(report){
 const lines=['Waste report — supplied account '+quoted(report.accountId),
  'Partial recorded observations; missing coverage is unknown. No unit or currency conversion.',
  'Records: '+report.coverage.records,
  'Unknown quantity: '+report.coverage.unknownQuantityRecords+' / '+report.coverage.records,
  'Unknown value: '+report.coverage.unknownValueRecords+' / '+report.coverage.records,
  'Quantities by recorded unit:'];
 for(const total of report.quantities)lines.push('  '+total.quantity+' '+quoted(total.unit));
 if(!report.quantities.length)lines.push('  No usable measured quantities.');
 lines.push('Values by recorded currency:');
 for(const total of report.values)lines.push('  '+total.amount+' '+quoted(total.currency)+' ('+total.knownRecords+' known records)');
 if(!report.values.length)lines.push('  No usable cost snapshots.');
 lines.push('Existing smaller-pack suggestions:');
 for(const s of report.suggestions)lines.push('  Receipt '+quoted(s.receiptId)+' / source '+quoted(s.sourceId)+' / season '+quoted(s.season)+': consider '+s.packSourceIds.map(quoted).join(', '));
 if(!report.suggestions.length)lines.push('  None supported by these records.');
 lines.push('Explicit zero is unaggregated by the positive-only helper; no purchase or stock action.');
 return lines.join('\n')+'\n';
}
try{
 const opts=options(process.argv.slice(2));
 if(opts.help)process.stdout.write(usage+'\n');
 else {
  const input=await readJSON(opts.input==='-'?process.stdin:createReadStream(opts.input));
  const result=analyzeWaste(input,{accountId:opts.account});
  const report={schema:'offmenu-waste-report/1',accountId:opts.account,...result};
  process.stdout.write(opts.json?JSON.stringify(report,null,2)+'\n':human(report));
 }
}catch(error){
 const json=process.argv.slice(2).includes('--json');
 process.stderr.write(json?JSON.stringify({error:'WASTE_REPORT_FAILED',message:error.message})+'\n':'Waste report failed: '+quoted(error.message)+'\n');process.exitCode=1;
}

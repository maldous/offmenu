import {IDENTIFIER_DB,IDENTIFIER_RUN,DETAIL_SELECTION} from '../../../public/scanner-identity-v2.js';
export function photoFixture() {
  const key={run_id:IDENTIFIER_RUN,input_id:'generated-source',record_ordinal:7,assertion_id:9};
  const reference={schema:'offmenu-identifier-observation/2',databaseSha256:IDENTIFIER_DB,runId:IDENTIFIER_RUN,
    namespace:'barcode',originalLexicalValue:'078742003986',sourceLexicalValue:'0078742003986',symbology:'UPC-A',
    matchType:'representation-alias',equivalence:'upc-a-as-leading-zero-ean-13',disposition:'source-asserted',
    sourceId:'off',releaseId:'2026-10-12',sourceRecordId:'generated-record',observationKey:key,detailSelectionSha256:DETAIL_SELECTION};
  const detail={referenceRecordId:'generated-record',sourceBinding:{sourceId:'off',releaseId:'2026-10-12'},
    observationKey:{databaseSha256:IDENTIFIER_DB,...key},
    sourceObservation:{...key,source_id:'off',release_id:'2026-10-12',namespace:'barcode',
      source_record_id:'generated-record',
      lexical_value:'0078742003986',disposition:'source-asserted'},
    records:[{data:{identifiers:[{system:'barcode',value:'0078742003986'}]}}]};
  return {reference,detail};
}

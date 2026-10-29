const forbidden=new Set(['rawFields','rawNutriments','ingredientsText','originalTextLines','sealed','credentials','owner','proofId']);
export function assertCurated(record){
 if(!record?.id?.startsWith('offmenu:')||record.provenance?.visibility!=='public'||record.curation?.schema!=='offmenu-curation/1'||record.curation.rawSourcePayloadPublished!==false)throw Error('Not an OffMenu curation record');
 function scan(value){if(!value||typeof value!=='object')return;for(const [key,item] of Object.entries(value)){if(forbidden.has(key))throw Error('Source/private payload cannot be published: '+key);scan(item);}}
 scan(record);return record;
}

// Pure retained-metadata adapter. No network, image bytes or use-right admission.
export const OFF_PHOTO_METADATA='offmenu-off-photo-metadata/1';
export const OFF_PHOTO_LICENSE=Object.freeze({name:'CC BY-SA 3.0',url:'https://creativecommons.org/licenses/by-sa/3.0/'});
const ROLES=['front','nutrition','ingredients','packaging'],SIZES=['display','small','thumb'];
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const text=v=>typeof v==='string'&&v.length>0&&v.length<=8192?v:null;
const code=v=>typeof v==='string'&&/^\d{1,32}$/.test(v)?v:null;
const integer=v=>typeof v==='string'&&/^\d{1,16}$/.test(v)?v:Number.isSafeInteger(v)&&v>=0?String(v):null;
const pointer=s=>s.replaceAll('~','~0').replaceAll('/','~1');
// This is OFF's storage-path convention, never an identity/equivalence join.
export function offPhotoStorageCode(value){
 if(!code(value))return null;
 const significant=value.replace(/^0+/,'')||'0';
 return significant.length<=8?significant.padStart(8,'0'):significant.length<=12?significant.padStart(13,'0'):significant;
}
function folder(value){const stored=offPhotoStorageCode(value);return stored?.length<=8?stored:stored?.replace(/^(...)(...)(...)(.*)$/,'$1/$2/$3/$4');}
function imageURL(value,sourceCode,role,language=null){
 if(!text(value)||value.length>4096)return null;
 try{const u=new URL(value),prefix='/images/products/'+folder(sourceCode)+'/';
  if(u.protocol!=='https:'||u.hostname!=='images.openfoodfacts.org'||u.port||u.username||u.password||u.search||u.hash||u.href!==value||!u.pathname.startsWith(prefix))return null;
  const match=/^(front|nutrition|ingredients|packaging)_([a-z]{2})\.(\d{1,16})\.(100|200|400|full)\.(?:jpg|jpeg|png|webp)$/.exec(u.pathname.slice(prefix.length));
  if(!match||match[1]!==role||language&&match[2]!==language)return null;
  return {url:value,role:match[1],language:match[2],revision:match[3],resolution:match[4],selectedKey:match[1]+'_'+match[2]};
 }catch{return null;}
}
const noticeFields=['title','copyright','copyright_notice','license_notice','disclaimer','attribution'];
function credit(sourceCode,photo,{selected=null,raw=null,catalogue=null}={}){
 const paths={selected:'/images/'+pointer(photo.selectedKey),raw:'/images/'+pointer(integer(selected?.imgid)||''),catalogue:'OFF_PHOTOS[key='+String(catalogue?.key||'')+']'};
 const notices=[];for(const [origin,entry]of [['selected',selected],['raw',raw],['catalogue',catalogue]])for(const field of noticeFields)if(text(entry?.[field]))notices.push({field,text:entry[field],origin,sourceField:paths[origin]+(origin==='catalogue'?'.':'/')+field});
 const uploader=text(raw?.uploader)||text(selected?.uploader)||text(catalogue?.contributor);
 const adaptations={};for(const field of ['imgid','rev','angle','normalize','white_magic','x1','x2','y1','y2','geometry','coordinates_image_size'])if(selected&&Object.hasOwn(selected,field)&&(selected[field]===null||typeof selected[field]==='boolean'||typeof selected[field]==='number'&&Number.isFinite(selected[field])||typeof selected[field]==='string'&&selected[field].length<=8192))adaptations[field]=selected[field];
 return {schema:OFF_PHOTO_METADATA,sourceName:'Open Food Facts',sourceCode,
  productUrl:'https://world.openfoodfacts.org/product/'+sourceCode,
  photoPage:'https://world.openfoodfacts.org/cgi/product_image.pl?code='+sourceCode+'&id='+photo.selectedKey,
  photoLicense:{...OFF_PHOTO_LICENSE,scope:'Publisher-stated product-photo licence; not database licensing'},
  databaseLicenses:[{name:'ODbL',url:'https://opendatacommons.org/licenses/odbl/1-0/'},{name:'DbCL',url:'https://opendatacommons.org/licenses/dbcl/1-0/'}],
  author:uploader?{value:uploader,role:'publisher-reported uploader; independent authorship unverified',sourceField:text(raw?.uploader)?paths.raw+'/uploader':text(selected?.uploader)?paths.selected+'/uploader':paths.catalogue+'.contributor'}:null,
  notices,adaptationProvenance:{retainedSourceSelection:adaptations,offmenuImageChanges:[],imageBytesFetched:false,imageBytesChanged:false,
   previousChanges:text(catalogue?.changes)||null,statement:'Metadata selection/URL construction only; no new image adaptation performed.'},
  packagingRights:{status:'not-universally-cleared',qualification:'Packaging artwork and other underlying rights remain separate; the photo licence alone does not establish all permissions for a proposed use.'},
  placement:'accessible-photo-details',compactHeaderCredit:false};
}

/** Extract at most one selected reference per role; metadata is NOT display authority. */
export function extractRetainedOFFPhotos(product,{selectedSourceCode,language=null}={}){
 const sourceCode=code(product?.code),packet={schema:OFF_PHOTO_METADATA,sourceCode,photos:[],unavailable:[],usePermissionEstablished:false,imageFetches:0};
 if(!object(product)||!sourceCode||selectedSourceCode!==sourceCode){packet.unavailable.push({reason:'exact-selected-source-code-mismatch-or-missing'});return packet;}
 const lang=typeof language==='string'&&/^[a-z]{2}$/.test(language)?language:null;
 for(const role of ROLES){
  let chosen=null,evidencePointer=null,kind=null;const rejected=[];
  if(lang)for(const size of SIZES){const value=product.selected_images?.[role]?.[size]?.[lang];if(value==null)continue;
   const candidate=imageURL(value,sourceCode,role,lang);if(candidate){chosen=candidate;evidencePointer='/selected_images/'+role+'/'+size+'/'+lang;kind='retained-selected-image-url';break;}
   rejected.push({pointer:'/selected_images/'+role+'/'+size+'/'+lang,reason:'URL-role-language-or-product-identity-not-qualified'});
  }
  if(!chosen)for(const field of ['image_'+role+'_url','image_'+role+'_small_url','image_'+role+'_thumb_url']){
   if(product[field]==null)continue;const candidate=imageURL(product[field],sourceCode,role,lang);
   if(candidate){chosen=candidate;evidencePointer='/'+field;kind='retained-image-role-url';break;}
   rejected.push({pointer:'/'+field,reason:'URL-role-or-product-identity-not-qualified'});
  }
  const key=lang?role+'_'+lang:null,selection=key&&object(product.images?.[key])?product.images[key]:null;
  if(!chosen&&selection){const revision=integer(selection.rev),resolution=['400','200','100','full'].find(size=>Object.hasOwn(selection.sizes||{},size));
   if(revision&&resolution){chosen=imageURL('https://images.openfoodfacts.org/images/products/'+folder(sourceCode)+'/'+key+'.'+revision+'.'+resolution+'.jpg',sourceCode,role,lang);evidencePointer='/images/'+pointer(key)+'/rev';kind='reconstructed-from-retained-image-revision-and-size';}
  }
  if(!chosen){packet.unavailable.push({role,reason:'no-qualified-retained-role-URL-or-explicit-revision-and-size',rejected});continue;}
  // Do not borrow an uploader/transform from a different revision/language.
  const boundSelection=object(product.images?.[chosen.selectedKey])&&integer(product.images[chosen.selectedKey].rev)===chosen.revision?product.images[chosen.selectedKey]:null;
  const rawId=integer(boundSelection?.imgid),raw=rawId&&object(product.images?.[rawId])?product.images[rawId]:null;
  packet.photos.push({...chosen,selectionKind:kind,sourcePointer:evidencePointer,sourceCode,
   imageId:rawId,availability:'metadata-reference-only; image bytes and display use unverified',
   attribution:credit(sourceCode,chosen,{selected:boundSelection,raw}),rejectedAlternatives:rejected});
 }
 return packet;
}

/** Map already-retained fixed-catalogue facts without pretending they are API fields. */
export function retainedCataloguePhotoAttribution(entry,selectedSourceCode){
 if(!object(entry)||!code(entry.sourceCode)||entry.sourceCode!==selectedSourceCode||entry.license!==OFF_PHOTO_LICENSE.name||entry.licenseUrl!==OFF_PHOTO_LICENSE.url)return null;
 const photo=imageURL(entry.url,entry.sourceCode,'front');if(!photo||photo.revision!==entry.revision)return null;
 return {...credit(entry.sourceCode,photo,{catalogue:entry}),retainedSourceUrl:entry.url,
  retainedSourcePage:entry.sourcePage,retainedPhotoLicensePage:entry.licensePage,
  imageId:entry.imageId,revision:entry.revision,sourceKind:'retained-fixed-catalogue-metadata',
  snapshotMembership:'unverified; current publisher observation only'};
}

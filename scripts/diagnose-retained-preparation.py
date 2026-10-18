#!/usr/bin/env python3
"""Read-only evidence for exact prior nonready preparations; no promotion or repair.

Caller holds collection/fixed-selection.lock and supplies the current manifest assets.
Only fixed paths are read. PDF facts reuse exact hash-bound prior parser details.
ZIP diagnostics inspect bounded directory/relationship metadata, never extract files.
"""
from contextlib import ExitStack
import errno,hashlib,io,json,math,os,re,stat,struct,time,zipfile
from pathlib import Path,PurePosixPath
import xml.etree.ElementTree as ET

SCHEMA='offmenu-retained-preparation-diagnostics/1'
OUTPUT_ROOT=Path('/home/user/src/offmenu-data/owner-collection-runtime')
EXPECTED_UID=1000
RESULT_SHA256='7e844aae16ed22b088c2643fec3f9722110cdad30b9f0fcc264c2db57eba4795'
MANIFEST_SHA256='d846a735762e627fbf69475da958f39fa68418bea19c6b186e516f9e7feef270'
GLOBAL_DETAIL_SHA256='7c20cb78e14570b42241a4c8cedc6d3018be1301210db713542aaa6734926f61'
MAX_SECONDS=60
MAX_HASH_BYTES=1024**3
MAX_METADATA_BYTES=8*1024**2
MAX_XML_BYTES=4*1024**2
MAX_REPORT_BYTES=16384
# Match the unchanged bounded-structural-preparation/2 guards.
MAX_MEMBERS=512;MAX_MEMBER_BYTES=32*1024**2;MAX_ARCHIVE_BYTES=128*1024**2
MAX_RATIO=200;MAX_PARSE_BYTES=128*1024**2
ENTRIES=({'assetIndex': 1693, 'assetId': 'file:086b611c2d09e000afc0a106', 'sourceKey': 'file:086b611c2d09e000afc0a106', 'path': '/home/user/src/offmenu-data/national-originals/bls/BLS-4.0.zip', 'size': 14263306, 'sha256': '12b7a6ba62807ec9b301eb276f897dc85f99b2292311618dec3749a12d984c91', 'priorDetailSHA256': '45bad9814eb05898dd3c92d219891e28c37af39cc94a2531b5702b5a21c65837', 'priorCode': 'member-contracts-required', 'media': 'application/zip'}, {'assetIndex': 1716, 'assetId': 'file:0bc57e06e6bd7bbf810aafe9', 'sourceKey': 'file:0bc57e06e6bd7bbf810aafe9', 'path': '/home/user/src/offmenu-data/national-originals/cofid/cofid2021.xlsx', 'size': 4629542, 'sha256': '436e9445ef2adb2a75f3d7edd51302de3adad25385f9795fc94ba58bd030e97d', 'priorDetailSHA256': '9ac56d8e245d27bab787e81516016076ec68c0393c415ea548f4a0e94b8203dd', 'priorCode': 'archive-unsafe', 'media': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}, {'assetIndex': 1875, 'assetId': 'file:2084c900936b97b4cfa86b11', 'sourceKey': 'file:2084c900936b97b4cfa86b11', 'path': '/home/user/src/offmenu-data/national-originals/mext-2023/20260327-mxt_kagsei-mext-000029402_0001.pdf', 'size': 5267334, 'sha256': 'd1196cc8fc5ddab1faa5e4a2b4ef9ed2ccc2ea333c9994ee79d9a49f2628f116', 'priorDetailSHA256': '84b048ae16010133916fc676a0fc75ac31c2776487fd4a4b7cda7aab72703f55', 'priorCode': 'pdf-encrypted', 'media': 'application/pdf'}, {'assetIndex': 1930, 'assetId': 'file:265945a007e9b7c1bcd62352', 'sourceKey': 'file:265945a007e9b7c1bcd62352', 'path': '/home/user/src/offmenu-data/national-originals/afcd/Food-Details.xlsx', 'size': 1137444, 'sha256': '69aa096c45cb0699db60a9c544442312e9ff09af587b99c42dc78bc26f689629', 'priorDetailSHA256': '8d04e0cfb763e07e8a5b2a5d2268e7817834768c45054be937af02de4abe8af6', 'priorCode': 'archive-unsafe', 'media': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}, {'assetIndex': 1947, 'assetId': 'file:27fb231193d3f16a4c2dc759', 'sourceKey': 'file:27fb231193d3f16a4c2dc759', 'path': '/home/user/src/offmenu-data/national-originals/mext-2023/20230428-mxt_kagsei-mext_00001_021.pdf', 'size': 1537993, 'sha256': '50042ac896a73964df4ea019fd3fe649fc2d84afc65498b970ce1fc1062f6af8', 'priorDetailSHA256': '20ad916e03d31899e7bba7c1f5d1e1a7dbbb168577d372652bf7ce4d97461ee7', 'priorCode': 'pdf-encrypted', 'media': 'application/pdf'}, {'assetIndex': 1988, 'assetId': 'file:2dcd91a8ab2ee38c4674c343', 'sourceKey': 'file:2dcd91a8ab2ee38c4674c343', 'path': '/home/user/src/offmenu-data/national-originals/afcd/Reference List.xlsx', 'size': 69194, 'sha256': '970bd41a4a85f172ca152c61561027c7970c70ed179e757a7b3c541e02497160', 'priorDetailSHA256': '074159f6b4e68b53accfd761e02cf6e9281c2e170790bc470287251021d738ad', 'priorCode': 'archive-unsafe', 'media': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}, {'assetIndex': 2226, 'assetId': 'file:4e3694a18542bbfcc11b388d', 'sourceKey': 'usda-archive:2026-04', 'path': '/home/user/src/offmenu-data/originals/FoodData_Central_csv_2026-04-30.zip', 'size': 481517495, 'sha256': 'c33d91e5c44ddbcd71ed6038714fb648b26089b3f91fabfa3be63d96d5763a01', 'priorDetailSHA256': '3548560c14cc0abce6d9ce022d035538aedc3e9f5cc7d8286bacaca17e05e07b', 'priorCode': 'parser-input-limit', 'media': 'application/zip'}, {'assetIndex': 2390, 'assetId': 'file:61d74972d339d7b9d8117501', 'sourceKey': 'file:61d74972d339d7b9d8117501', 'path': '/home/user/src/offmenu-data/national-originals/afcd/Nutrient-details.xlsx', 'size': 107383, 'sha256': '7c455129a90e65d29840ecd188fa223cca8bdf0729b21efebc286884d69fafaa', 'priorDetailSHA256': 'e04c608909310cfc4b413002379b15af2ef8d59e74a6ee304217411de3cf5c36', 'priorCode': 'archive-unsafe', 'media': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}, {'assetIndex': 2706, 'assetId': 'file:8f2401cc8c0384d79cdc560d', 'sourceKey': 'file:8f2401cc8c0384d79cdc560d', 'path': '/home/user/src/offmenu-data/national-originals/bls/BLS_4_0_2025_DE/BLS_4_0_Daten_2025_DE.xlsx', 'size': 14093078, 'sha256': '524bbefe25b691f5cb3de7a9f3e27fa2967aebfeabf217d99414ba7806e78c60', 'priorDetailSHA256': '57a1ecf4d73e4093c88c95af4ab76e0a56da7c947ddf893024aa8bd73737ed27', 'priorCode': 'archive-expansion-limit', 'media': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}, {'assetIndex': 2927, 'assetId': 'file:af6e1776abe7bf5f65da8893', 'sourceKey': 'file:af6e1776abe7bf5f65da8893', 'path': '/home/user/src/offmenu-data/national-originals/afcd/Recipes.xlsx', 'size': 109100, 'sha256': '81925cd790b4d914e9016fe71e273e4b5823cbcea7d6aafc277ebbc160e762ef', 'priorDetailSHA256': 'bffb5cb3392b19f77d2c23c0145ab0a0d3d964d10e853a216d04b0f0425389f7', 'priorCode': 'archive-unsafe', 'media': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}, {'assetIndex': 3198, 'assetId': 'file:d70c5a3077ed90879f557da9', 'sourceKey': 'file:d70c5a3077ed90879f557da9', 'path': '/home/user/src/offmenu-data/national-originals/afcd/Nutrient-profiles.xlsx', 'size': 2107021, 'sha256': '14cb3e73dbf58987b440e6299624c0fefd7a4e61591fc1f753995d9534e0efc9', 'priorDetailSHA256': '38c1d72e7897608c54302c6790b1ad8a125b5a9d1fbefc69d18df418758eec2b', 'priorCode': 'archive-unsafe', 'media': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}, {'assetIndex': 3228, 'assetId': 'file:dad2c71bdbe00e0c5483915a', 'sourceKey': 'file:dad2c71bdbe00e0c5483915a', 'path': '/home/user/src/offmenu-data/national-originals/mext-2023/20230428-mxt_kagsei-mext_00001_041.pdf', 'size': 1564429, 'sha256': 'd02b814b4900438c2abf40d566cc3f17d0719e20d120fe0434565563c638cc43', 'priorDetailSHA256': 'ec1bd338fbf4feb706c11d38093d4fd3332cfef8d7a15a2f3a3eec297aa9b5d0', 'priorCode': 'pdf-encrypted', 'media': 'application/pdf'}, {'assetIndex': 3356, 'assetId': 'file:ea866f2a2fe316175e429adb', 'sourceKey': 'file:ea866f2a2fe316175e429adb', 'path': '/home/user/src/offmenu-data/national-originals/mext-2023/20230428-mxt_kagsei-mext_00001_031.pdf', 'size': 1246667, 'sha256': '79588a2b9532a4aeac1dfbddb2b217b440f8879cc3309c56bdf484a13ecadfd6', 'priorDetailSHA256': '7d5c0eba8b983ddb334e809224cc2a9667c4a8ac7ec851fee3974e12c195b075', 'priorCode': 'pdf-encrypted', 'media': 'application/pdf'}, {'assetIndex': 3389, 'assetId': 'file:ee5ac5084fcd3ab0ece15da9', 'sourceKey': 'file:ee5ac5084fcd3ab0ece15da9', 'path': '/home/user/src/offmenu-data/national-originals/mext-2023/20230525-mxt_kagsei-mext_00001_001.pdf', 'size': 2546710, 'sha256': '9aaa3fc6afaf3208f2c6b806f12cb7601cc24b17a7d5ef8ef965a129d39360b9', 'priorDetailSHA256': '31d91f082ff910ede27bd6ac3a5869ac4ec8fc9e46280f6aacd08eb0305c61df', 'priorCode': 'pdf-encrypted', 'media': 'application/pdf'}, {'assetIndex': 3453, 'assetId': 'file:f6ad19a5af6f95b5de94130a', 'sourceKey': 'file:f6ad19a5af6f95b5de94130a', 'path': '/home/user/src/offmenu-data/national-originals/afcd/Food group information.xlsx', 'size': 904432, 'sha256': 'e2d0507394ce5c2abe1f186d36058affa6d532c0d50ea18cf98908e368e17e90', 'priorDetailSHA256': 'bea9a5236e4ae4eec78a23269107114b7bcc0a164eed88b391cdc1de15ca5d57', 'priorCode': 'archive-unsafe', 'media': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}, {'assetIndex': 4732, 'assetId': 'source:ba08-alterural-cooking-booklet-original-20261018', 'sourceKey': 'ba08-alterural-cooking-booklet-original-20261018', 'path': '/srv/offmenu-refresh/outputs/collection/source-cache/objects/805406e0924089b9c14ec366ab294dc96030e5f38625fa61498305a29ee06f40', 'size': 3105263, 'sha256': '805406e0924089b9c14ec366ab294dc96030e5f38625fa61498305a29ee06f40', 'priorDetailSHA256': '2fae319e2617abfd9f499402643c708db1374db9722e89a6d7a9e0225ea75ca9', 'priorCode': 'original-unavailable', 'media': 'application/pdf'}, {'assetIndex': 4735, 'assetId': 'source:ch.fsvo.food-composition.v7_1.xlsx', 'sourceKey': 'ch.fsvo.food-composition.v7_1.xlsx', 'path': '/srv/offmenu-refresh/outputs/collection/source-cache/objects/323bae2eecd639d2c3b3bf3797d30b1426ccb0253fb62810f522778b38089196', 'size': 1014249, 'sha256': '323bae2eecd639d2c3b3bf3797d30b1426ccb0253fb62810f522778b38089196', 'priorDetailSHA256': '24fb46497391324339db9c4a5e2944d46f912bf48e124fa5bf433be6e4d7fdfa', 'priorCode': 'original-unavailable', 'media': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}, {'assetIndex': 4742, 'assetId': 'source:py-drive-health2', 'sourceKey': 'py-drive-health2', 'path': '/home/user/src/offmenu-data/owner-collection-runtime/collection/private-originals/13a65d6a69c6ea61e10d5a5d091512105f1918c8e3b10e9e3471592bd6b29deb/original.pdf', 'size': 7587546, 'sha256': '442f4518e5f42ef753627424817ae0c5774753f6d7cc5de1b6ec61e91b096942', 'priorDetailSHA256': '0ca8122674b1f0323d4b02613ef605aa09fcf8554b4c0f0a40b3ebeb51632c07', 'priorCode': 'pdf-ocr-required', 'media': 'application/pdf'}, {'assetIndex': 4743, 'assetId': 'source:py-drive-school1', 'sourceKey': 'py-drive-school1', 'path': '/home/user/src/offmenu-data/owner-collection-runtime/collection/private-originals/ec26eca78d79af04f779c7bb0d0e5740a83339a17c3bc4f83624a999c507b3b9/original.pdf', 'size': 30653686, 'sha256': 'ec9ea4b8560927face8d1a099625fc453c2321f6d190e26eb628a41f7e6af466', 'priorDetailSHA256': '2a8651e6e46c548e96678b675e3416bf95678155e81ace817e762e42f666e807', 'priorCode': 'pdf-ocr-required', 'media': 'application/pdf'}, {'assetIndex': 4744, 'assetId': 'source:py-drive-school2', 'sourceKey': 'py-drive-school2', 'path': '/home/user/src/offmenu-data/owner-collection-runtime/collection/private-originals/72eb60e3a5984d8b5e09ae84792daae22851092e1bfb99b8ce6af5f44afc82ea/original.pdf', 'size': 73938718, 'sha256': '115d81ceab51403a2d2be5f69dbeda4f2fa54e2393b4d917f48de4638da0930b', 'priorDetailSHA256': 'da87a19b1c1d843d9668d7f6730928fb14f336e3ad356eb8d979a3670dfc2721', 'priorCode': 'pdf-ocr-required', 'media': 'application/pdf'}, {'assetIndex': 4745, 'assetId': 'source:py-drive-veg', 'sourceKey': 'py-drive-veg', 'path': '/home/user/src/offmenu-data/owner-collection-runtime/collection/private-originals/7f13d163d6d979a2f9f004d000dbb72494a0228d7303b389e03d58405f0b2daa/original.pdf', 'size': 17928840, 'sha256': '2223cb39b7b12c4df0dbb5da7295cbeab2adeec7a59fc4e43363eb2f87586ecc', 'priorDetailSHA256': '7fdf45a3fc43ff3615a195b1df8ef8e4ca390b6dda7c1da0af3cfe17e2b94d0e', 'priorCode': 'pdf-ocr-required', 'media': 'application/pdf'}, {'assetIndex': 4746, 'assetId': 'source:sb20-helti-kaikai-2025-whole-original-20261018', 'sourceKey': 'sb20-helti-kaikai-2025-whole-original-20261018', 'path': '/srv/offmenu-refresh/outputs/collection/source-cache/objects/133e96044ab6d7d26bf2158deccd0d9d96daee75381bba5795d7039712d9bc1c', 'size': 27578590, 'sha256': '133e96044ab6d7d26bf2158deccd0d9d96daee75381bba5795d7039712d9bc1c', 'priorDetailSHA256': '0b3448d4790feaf4f409e34cd936f18e03b22ed532f8e7f828da9d2e15d46b34', 'priorCode': 'original-unavailable', 'media': 'application/pdf'})
ERRORS={'diagnostic-deadline','diagnostic-byte-budget','current-asset-unresolved','current-stage-held',
 'read-permission-unestablished','root-mismatch','owner-mismatch','path-absent','permission-denied',
 'unsafe-path','not-regular','extent-mismatch','digest-mismatch','changed-during-read','local-io-error',
 'prior-detail-unavailable','prior-detail-invalid','archive-invalid','relationship-xml-invalid',
 'relationship-metadata-limit','relationship-xml-unsafe','diagnostic-invalid'}
ARCHIVE_REASONS={'multidisk','entry-count','central-directory-size','central-directory-bounds',
 'comment-extent','zip64-unsupported','member-name','duplicate-name','encrypted-member','special-member','compression-method',
 'executable-member','member-size','expanded-total','compression-ratio'}
REL_REASONS={'external','parent-component','backslash','absolute-outside-xl','missing-target','duplicate-id','missing-id'}
SAFETY={'networkRequests':0,'filesChanged':False,'sourceClaimsChanged':False,'sourceBodiesUploaded':False,
 'passwordsAttempted':False,'guardsRelaxed':False,'originalsPromoted':False,'pdfParserExecuted':False}

def canonical(value):
 return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()+b'\n'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def check(deadline):
 if time.monotonic()>=deadline:raise ValueError('diagnostic-deadline')
def identity(s):return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode,s.st_uid,s.st_nlink)
def safe_open(stack,path):
 path=Path(path)
 if not path.is_absolute() or '..' in path.parts:raise ValueError('unsafe-path')
 flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK
 fd=os.open('/',flags|os.O_DIRECTORY);stack.callback(os.close,fd)
 for part in path.parts[1:-1]:
  fd=os.open(part,flags|os.O_DIRECTORY,dir_fd=fd);stack.callback(os.close,fd)
 parent=fd;name=path.name
 fd=os.open(name,flags,dir_fd=parent);stack.callback(os.close,fd)
 before=identity(os.fstat(fd))
 if not stat.S_ISREG(before[5]):raise ValueError('not-regular')
 return fd,parent,name,before

def unchanged(opened,path):
 fd,parent,name,before=opened
 try:
  if identity(os.fstat(fd))!=before or identity(os.stat(name,dir_fd=parent,follow_symlinks=False))!=before:
   raise ValueError('changed-during-read')
  # The old parent descriptor survives rename; verify the complete fixed path too.
  with ExitStack() as stack:
   rebound=safe_open(stack,path)
   if rebound[3]!=before:raise ValueError('changed-during-read')
 except (OSError,ValueError):raise ValueError('changed-during-read') from None

def read_json(path,expected,deadline):
 with ExitStack() as stack:
  opened=safe_open(stack,path);fd,_,_,before=opened
  if before[2]>MAX_METADATA_BYTES:raise ValueError('prior-detail-invalid')
  chunks=[];count=0
  while True:
   check(deadline);block=os.read(fd,min(65536,MAX_METADATA_BYTES-count+1));check(deadline)
   if not block:break
   count+=len(block)
   if count>MAX_METADATA_BYTES:raise ValueError('prior-detail-invalid')
   chunks.append(block)
  unchanged(opened,path);raw=b''.join(chunks)
  if sha(raw)!=expected:raise ValueError('prior-detail-invalid')
  def unique(pairs):
   out={}
   for k,v in pairs:
    if k in out:raise ValueError('prior-detail-invalid')
    out[k]=v
   return out
  return json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('prior-detail-invalid')))

def error_code(exc):
 if isinstance(exc,ValueError) and str(exc) in ERRORS:return str(exc)
 if isinstance(exc,FileNotFoundError):return 'path-absent'
 if isinstance(exc,PermissionError):return 'permission-denied'
 if isinstance(exc,OSError) and exc.errno in {errno.ELOOP,errno.ENOTDIR}:return 'unsafe-path'
 if isinstance(exc,OSError):return 'local-io-error'
 return 'diagnostic-invalid'

def archive_facts(stream,size,deadline,relationships=False):
 """Directory bounds are checked BEFORE ZipFile allocates its directory objects."""
 check(deadline);stream.seek(max(0,size-65557));tail=stream.read(65557);check(deadline)
 at=tail.rfind(b'PK\x05\x06')
 if at<0 or at+22>len(tail):raise ValueError('archive-invalid')
 _,disk,central_disk,on_disk,entries,central_size,offset,comment=struct.unpack('<4s4H2IH',tail[at:at+22])
 marker=max(0,size-65557)+at
 reasons=set()
 if disk or central_disk or on_disk!=entries:reasons.add('multidisk')
 if tail[max(0,at-20):at].startswith(b'PK\x06\x07') or entries==65535 or central_size==0xffffffff or offset==0xffffffff:reasons.add('zip64-unsupported')
 if not 1<=entries<=MAX_MEMBERS:reasons.add('entry-count')
 if central_size>MAX_MEMBERS*1024:reasons.add('central-directory-size')
 if offset+central_size>marker:reasons.add('central-directory-bounds')
 if marker+22+comment!=size:reasons.add('comment-extent')
 result={'entries':entries,'centralBytes':central_size,'largestMemberBytes':0,'expandedBytes':0,
  'maximumRatioCeil':0,'reasons':sorted(reasons),'relationships':None}
 if reasons:return result
 with zipfile.ZipFile(stream) as archive:
  members=archive.infolist();names=set();total=0
  if len(members)!=entries:reasons.add('entry-count')
  for member in members:
   check(deadline);name=member.filename;parts=PurePosixPath(name);mode=member.external_attr>>16
   if (len(name.encode('utf-8'))>512 or '\x00' in name or '\\' in name or ':' in name or parts.is_absolute()
       or '..' in parts.parts or not parts.parts or name.startswith('./') or '//' in name or '/./' in name):reasons.add('member-name')
   if name.casefold() in names:reasons.add('duplicate-name')
   names.add(name.casefold())
   if member.flag_bits&1:reasons.add('encrypted-member')
   if stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR):reasons.add('special-member')
   if member.compress_type not in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED):reasons.add('compression-method')
   if name.casefold().endswith(('vbaproject.bin','.exe','.dll','.js','.vbs','.ps1')):reasons.add('executable-member')
   total+=member.file_size;ratio=(member.file_size+max(1,member.compress_size)-1)//max(1,member.compress_size)
   result['largestMemberBytes']=max(result['largestMemberBytes'],member.file_size)
   result['maximumRatioCeil']=max(result['maximumRatioCeil'],ratio)
   if member.file_size>MAX_MEMBER_BYTES:reasons.add('member-size')
   if total>MAX_ARCHIVE_BYTES:reasons.add('expanded-total')
   if member.file_size>max(1,member.compress_size)*MAX_RATIO:reasons.add('compression-ratio')
  result.update(expandedBytes=total,reasons=sorted(reasons))
  if relationships and not reasons:result['relationships']=relationship_facts(archive,deadline)
 check(deadline);return result

def relationship_facts(archive,deadline):
 name='xl/_rels/workbook.xml.rels'
 try:member=archive.getinfo(name)
 except KeyError:raise ValueError('relationship-xml-invalid') from None
 if member.file_size>MAX_XML_BYTES:raise ValueError('relationship-metadata-limit')
 with archive.open(member) as stream:
  raw=stream.read(MAX_XML_BYTES+1);check(deadline)
 if len(raw)>MAX_XML_BYTES:raise ValueError('relationship-metadata-limit')
 try:text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
 except UnicodeError:raise ValueError('relationship-xml-invalid') from None
 if '\x00' in text or re.search(r'<!\s*(?:DOCTYPE|ENTITY)\b',text,re.I):raise ValueError('relationship-xml-unsafe')
 names=set(archive.namelist());root=None;depth=0;count=0
 try:
  for event,node in ET.iterparse(io.StringIO(text),events=('start','end')):
   check(deadline)
   if event=='start':
    depth+=1;count+=1
    if root is None:root=node
    if depth>128 or count>10000:raise ValueError('relationship-metadata-limit')
   else:depth-=1
 except ET.ParseError:raise ValueError('relationship-xml-invalid') from None
 counts={reason:0 for reason in sorted(REL_REASONS)};seen=set();internal=0;worksheet=0
 for item in root:
  check(deadline);target=item.get('Target','');rid=item.get('Id');external=item.get('TargetMode')=='External'
  normalized=target.lstrip('/') if target.startswith('/xl/') else 'xl/'+target
  if external:counts['external']+=1
  if '..' in PurePosixPath(normalized).parts:counts['parent-component']+=1
  if '\\' in normalized:counts['backslash']+=1
  if target.startswith('/') and not target.startswith('/xl/'):counts['absolute-outside-xl']+=1
  if not external and normalized not in names:counts['missing-target']+=1
  if rid is None:counts['missing-id']+=1
  elif rid in seen:counts['duplicate-id']+=1
  seen.add(rid)
  if not external:internal+=1
  if item.get('Type','').endswith('/worksheet'):worksheet+=1
 return {'count':len(root),'internal':internal,'worksheet':worksheet,'reasons':counts}

def current_permission(asset,entry):
 if not isinstance(asset,dict) or asset.get('assetId')!=entry['assetId']:return 'current-asset-unresolved'
 contract=asset.get('preparationContract') or asset.get('preparationTemplate')
 if asset.get('sourceStageHolds') or set(asset.get('holds',[]))&{'read','extract','copy','all'} or (isinstance(contract,dict) and contract.get('holds')):return 'current-stage-held'
 if not isinstance(contract,dict) or contract.get('permissions',{}).get('read') is not True:return 'read-permission-unestablished'
 if contract.get('permissions',{}).get('extract') is not True:return 'current-stage-held'
 return None

def prior_preparations(output_root,deadline):
 folder=output_root/'collection/global-collection'/MANIFEST_SHA256
 detail=read_json(folder/('result-'+GLOBAL_DETAIL_SHA256+'.json'),GLOBAL_DETAIL_SHA256,deadline)
 if detail.get('schemaVersion')!='offmenu-global-collection-detail/1' or not isinstance(detail.get('checkpoints'),list):raise ValueError('prior-detail-invalid')
 checkpoints={}
 for pair in detail['checkpoints']:
  if not isinstance(pair,list) or len(pair)!=2 or type(pair[0]) is not int or not isinstance(pair[1],str) or not re.fullmatch('[0-9a-f]{64}',pair[1]) or pair[0] in checkpoints:raise ValueError('prior-detail-invalid')
  checkpoints[pair[0]]=pair[1]
 return folder,checkpoints

def prior_item(folder,checkpoints,entry,deadline):
 digest=checkpoints.get(entry['assetIndex'])
 if digest is None:raise ValueError('prior-detail-unavailable')
 checkpoint=read_json(folder/('asset-'+str(entry['assetIndex'])+'-'+digest+'.json'),digest,deadline)
 detail=checkpoint.get('detail',{}).get('preparation')
 if checkpoint.get('assetId')!=entry['assetId'] or checkpoint.get('manifestSHA256')!=MANIFEST_SHA256 or not isinstance(detail,dict) or sha(canonical(detail))!=entry['priorDetailSHA256']:raise ValueError('prior-detail-invalid')
 return detail

def item_template(entry):
 return {'assetIndex':entry['assetIndex'],'assetId':entry['assetId'],'priorCode':entry['priorCode'],
  'status':'blocked','errorCode':None,'access':'unobserved','bytesHashed':0,'identityVerified':False,
  'priorDetailVerified':False,'archive':None,'pdf':None,
  'capability':('bounded-member-contracts-required' if entry['priorCode']=='member-contracts-required' else
                'streaming-archive-handler-required' if entry['priorCode']=='parser-input-limit' else
                'owner-readable-original-required' if entry['priorCode']=='original-unavailable' else None)}

def diagnose_one(entry,asset,deadline,budget,prior):
 result=item_template(entry)
 try:
  check(deadline);error=current_permission(asset,entry)
  if error:raise ValueError(error)
  with ExitStack() as stack:
   opened=safe_open(stack,entry['path']);fd,_,_,before=opened;result['access']='readable'
   if before[2]!=entry['size']:raise ValueError('extent-mismatch')
   if before[2]>MAX_HASH_BYTES-budget[0]:raise ValueError('diagnostic-byte-budget')
   digest=hashlib.sha256()
   while result['bytesHashed']<before[2]:
    check(deadline);block=os.read(fd,min(65536,before[2]-result['bytesHashed']))
    if not block:raise ValueError('changed-during-read')
    budget[0]+=len(block);result['bytesHashed']+=len(block);digest.update(block);check(deadline)
   unchanged(opened,entry['path'])
   if digest.hexdigest()!=entry['sha256']:raise ValueError('digest-mismatch')
   result['identityVerified']=True
   detail=None
   if prior is not None:
    try:detail=prior_item(*prior,entry,deadline);result['priorDetailVerified']=True
    except (OSError,ValueError,KeyError,TypeError):pass
   if entry['media']=='application/pdf':
    metrics=(detail.get('metrics') or {}) if detail else {}
    page=metrics.get('pageCount');blank=metrics.get('pagesWithoutText');selected=metrics.get('selectedPageCount')
    result['pdf']={'factsFromPriorParser':detail is not None,'encryptedFlagObserved':True if detail and entry['priorCode']=='pdf-encrypted' else None,
     'passwordRequired':None,'pageCount':page if type(page) is int else None,
     'selectedPageCount':selected if type(selected) is int else None,'pagesWithoutText':blank if type(blank) is int else None,
     'pagesWithText':selected-blank if type(selected) is int and type(blank) is int and 0<=blank<=selected else None,
     'ocrPerformed':False,'imageOnlyEstablished':False,'parser':(detail.get('parser') or {}).get('name') if detail else None}
    if detail is None:raise ValueError('prior-detail-unavailable')
   elif entry['media'] in {'application/zip','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}:
    # Reading the central directory does not decompress the 481MB USDA archive.
    with os.fdopen(os.dup(fd),'rb') as stream:
     result['archive']=archive_facts(stream,before[2],deadline,entry['media']!='application/zip')
   unchanged(opened,entry['path']);check(deadline);result['status']='observed'
 except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile,RuntimeError,NotImplementedError) as exc:
  result['errorCode']=error_code(exc)
  if result['errorCode']=='changed-during-read':result['identityVerified']=False
  if result['access']=='unobserved' and result['errorCode'] in {'path-absent','permission-denied','unsafe-path','not-regular'}:result['access']=result['errorCode']
 return result

def run_diagnostics(output_root,absolute_deadline,*,assets):
 valid_deadline=type(absolute_deadline) in (int,float) and math.isfinite(absolute_deadline)
 deadline=min(absolute_deadline,time.monotonic()+MAX_SECONDS) if valid_deadline else time.monotonic()
 report={'schemaVersion':SCHEMA,'priorResultSHA256':RESULT_SHA256,'status':'complete','maximumSeconds':MAX_SECONDS,
  'maximumHashBytes':MAX_HASH_BYTES,'bytesHashed':0,'items':[],**SAFETY}
 root_error='diagnostic-invalid' if not valid_deadline else 'root-mismatch' if Path(output_root)!=OUTPUT_ROOT else 'owner-mismatch' if os.getuid()!=EXPECTED_UID else None
 prior=None
 if not root_error:
  try:prior=prior_preparations(Path(output_root),deadline)
  except (OSError,ValueError,KeyError,TypeError):pass
 byid={}
 for asset in assets if isinstance(assets,list) and len(assets)<=10000 else []:
  if isinstance(asset,dict):byid.setdefault(asset.get('assetId'),[]).append(asset)
 budget=[0]
 for entry in ENTRIES:
  matches=byid.get(entry['assetId'],[])
  if root_error:
   result=item_template(entry);result['errorCode']=root_error
  else:result=diagnose_one(entry,matches[0] if len(matches)==1 else None,deadline,budget,prior)
  report['items'].append(result)
 report['bytesHashed']=budget[0]
 if any(x['status']=='blocked' for x in report['items']):report['status']='complete-with-blocked'
 return sanitize_diagnostics(report)

def sanitize_diagnostics(report):
 keys={'schemaVersion','priorResultSHA256','status','maximumSeconds','maximumHashBytes','bytesHashed','items'}|set(SAFETY)
 if not isinstance(report,dict) or set(report)!=keys or report['schemaVersion']!=SCHEMA or report['priorResultSHA256']!=RESULT_SHA256 or report['status'] not in {'complete','complete-with-blocked'}:raise ValueError('invalid-retained-preparation-diagnostics')
 if any(type(report[k]) is not type(v) or report[k]!=v for k,v in SAFETY.items()):raise ValueError('invalid-retained-preparation-diagnostics')
 if report['maximumSeconds']!=MAX_SECONDS or report['maximumHashBytes']!=MAX_HASH_BYTES or type(report['bytesHashed']) is not int or not 0<=report['bytesHashed']<=MAX_HASH_BYTES or len(report['items'])!=len(ENTRIES):raise ValueError('invalid-retained-preparation-diagnostics')
 for entry,item in zip(ENTRIES,report['items']):
  template=item_template(entry)
  if not isinstance(item,dict) or set(item)!=set(template) or any(item[k]!=template[k] for k in ('assetIndex','assetId','priorCode','capability')):raise ValueError('invalid-retained-preparation-diagnostics')
  if item['status'] not in {'blocked','observed'} or item['errorCode'] not in ERRORS|{None} or item['access'] not in {'unobserved','readable','path-absent','permission-denied','unsafe-path','not-regular'}:raise ValueError('invalid-retained-preparation-diagnostics')
  if (item['status']=='observed')!=(item['errorCode'] is None):raise ValueError('invalid-retained-preparation-diagnostics')
  if type(item['bytesHashed']) is not int or not 0<=item['bytesHashed']<=entry['size'] or any(type(item[k]) is not bool for k in ('identityVerified','priorDetailVerified')):raise ValueError('invalid-retained-preparation-diagnostics')
  if item['identityVerified'] and (item['bytesHashed']!=entry['size'] or item['access']!='readable'):raise ValueError('invalid-retained-preparation-diagnostics')
  if item['status']=='observed' and not item['identityVerified']:raise ValueError('invalid-retained-preparation-diagnostics')
  archive=item['archive']
  if archive is not None:
   if entry['media'] not in {'application/zip','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}:raise ValueError('invalid-retained-preparation-diagnostics')
   if set(archive)!={'entries','centralBytes','largestMemberBytes','expandedBytes','maximumRatioCeil','reasons','relationships'} or any(type(archive[k]) is not int or not 0<=archive[k]<=2**80 for k in ('entries','centralBytes','largestMemberBytes','expandedBytes','maximumRatioCeil')) or archive['reasons']!=sorted(set(archive['reasons'])) or any(x not in ARCHIVE_REASONS for x in archive['reasons']):raise ValueError('invalid-retained-preparation-diagnostics')
   rel=archive['relationships']
   if rel is not None:
    if set(rel)!={'count','internal','worksheet','reasons'} or set(rel['reasons'])!=REL_REASONS or any(type(v) is not int or not 0<=v<=10000 for v in [rel['count'],rel['internal'],rel['worksheet'],*rel['reasons'].values()]):raise ValueError('invalid-retained-preparation-diagnostics')
  pdf=item['pdf']
  if pdf is not None:
   if entry['media']!='application/pdf':raise ValueError('invalid-retained-preparation-diagnostics')
   if set(pdf)!={'factsFromPriorParser','encryptedFlagObserved','passwordRequired','pageCount','selectedPageCount','pagesWithoutText','pagesWithText','ocrPerformed','imageOnlyEstablished','parser'}:raise ValueError('invalid-retained-preparation-diagnostics')
   if type(pdf['factsFromPriorParser']) is not bool or (pdf['encryptedFlagObserved'] is not None and pdf['encryptedFlagObserved'] is not True) or pdf['passwordRequired'] is not None or pdf['ocrPerformed'] is not False or pdf['imageOnlyEstablished'] is not False or pdf['parser'] not in (None,'pypdf','poppler','poppler-pdftotext'):raise ValueError('invalid-retained-preparation-diagnostics')
   if any(v is not None and (type(v) is not int or not 0<=v<=2000) for v in [pdf[k] for k in ('pageCount','selectedPageCount','pagesWithoutText','pagesWithText')]):raise ValueError('invalid-retained-preparation-diagnostics')
 if report['status']!=('complete-with-blocked' if any(x['status']=='blocked' for x in report['items']) else 'complete'):raise ValueError('invalid-retained-preparation-diagnostics')
 if sum(x['bytesHashed'] for x in report['items'])!=report['bytesHashed'] or len(canonical(report))>MAX_REPORT_BYTES:raise ValueError('invalid-retained-preparation-diagnostics')
 return report

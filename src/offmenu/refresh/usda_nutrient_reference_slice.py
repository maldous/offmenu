"""One explicitly selected retained-archive reference slice; no discovery or retries.

Caller supplies the actual operation selection, custody and code admission.
This reader verifies its supplied byte/row witnesses; it never grants permission.
"""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import time
import zipfile

VERSION='offmenu.usda-nutrient-reference-slice/1'
MAX_SOURCE=600*1024**2
MAX_EXPANDED=1024**2
MAX_ROWS=600


def identity(s):
    return [s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns]


def native_id_digest(ids):
    h=hashlib.sha256()
    for value in sorted(set(ids),key=lambda x:x.encode('utf-8')):
        h.update((json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode())
    return h.hexdigest()


class CountedSource:
    """Count actual returned descriptor bytes, including repeat reads after seeks."""
    def __init__(self,stream,maximum,deadline):
        self.stream=stream;self.maximum=maximum;self.deadline=deadline;self.bytes=0
        self.calls=0;self.stage='hash';self.stage_bytes={'hash':0,'zip':0}

    def guard(self):
        if time.monotonic()>self.deadline:raise ValueError('usda-slice-wall-limit')

    def tell(self):return self.stream.tell()
    def seek(self,*args):self.guard();return self.stream.seek(*args)
    def seekable(self):return True
    def readable(self):return True

    def read(self,n=-1):
        self.guard()
        if n<0:n=max(0,os.fstat(self.stream.fileno()).st_size-self.tell())
        if self.bytes+n>self.maximum:raise ValueError('usda-slice-source-read-limit')
        data=self.stream.read(n);self.calls+=1;self.bytes+=len(data);self.stage_bytes[self.stage]+=len(data)
        self.guard();return data


def read_selected_archive(path, *, expected_sha256, expected_bytes, specs,
                          source_read_limit=MAX_SOURCE, expanded_limit=MAX_EXPANDED,
                          row_limit=MAX_ROWS, wall_seconds=300):
    """Fresh full hash on one RO FD, then just two selected CSV member bodies.

    Specs bind exact member/name/columns/count/bytes/CRC/native-ID witness. They
    are metadata, not authority. No SQLite, other member extraction or source writes.
    Returns source rows only after all selected checks and final identity check.
    """
    if not (0<source_read_limit<=MAX_SOURCE and 0<expanded_limit<=MAX_EXPANDED and
            0<row_limit<=MAX_ROWS and 0<wall_seconds<=300):raise ValueError('usda-slice-limits')
    if len(specs)!=2 or {s['table'] for s in specs}!={'nutrient','measure_unit'}:
        raise ValueError('usda-slice-table-selection')
    if sum(s['rows'] for s in specs)>row_limit:raise ValueError('usda-slice-row-limit')
    path=Path(path);started=time.monotonic();deadline=started+wall_seconds
    if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('usda-slice-symlink')
    fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb',buffering=0) as stream:
        before=os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size!=expected_bytes:
            raise ValueError('usda-slice-original-type-size')
        observed=identity(before)
        if identity(path.lstat())!=observed:raise ValueError('usda-slice-identity')
        source=CountedSource(stream,source_read_limit,deadline);h=hashlib.sha256()
        while True:
            data=source.read(min(1024**2,expected_bytes-source.tell()+1))
            if not data:break
            h.update(data)
        actual_sha=h.hexdigest()
        if actual_sha!=expected_sha256:raise ValueError('usda-slice-original-sha')
        if identity(os.fstat(stream.fileno()))!=observed:raise ValueError('usda-slice-identity')
        source.stage='zip';rows=[];members=[];expanded=0
        with zipfile.ZipFile(source) as archive:
            names=[i.filename for i in archive.infolist()]
            for spec in specs:
                source.guard();name=spec['member']
                if names.count(name)!=1:raise ValueError('usda-slice-member-ambiguous')
                info=archive.getinfo(name)
                if (info.flag_bits&1 or info.is_dir() or info.file_size!=spec['bytes'] or
                    info.CRC!=spec['crc32'] or info.file_size>expanded_limit-expanded):
                    raise ValueError('usda-slice-member-metadata')
                with archive.open(info,'r') as body:
                    raw=body.read(info.file_size+1)
                if len(raw)!=info.file_size:raise ValueError('usda-slice-member-size')
                expanded+=len(raw)
                reader=csv.reader(io.StringIO(raw.decode('utf-8-sig'),newline=''),strict=True)
                if next(reader,None)!=spec['columns']:raise ValueError('usda-slice-header')
                native_ids=[];member_rows=[]
                for ordinal,values in enumerate(reader,1):
                    source.guard()
                    if ordinal>spec['rows'] or len(rows)+ordinal>row_limit:raise ValueError('usda-slice-row-limit')
                    if len(values)!=len(spec['columns']):raise ValueError('usda-slice-row-width')
                    fields=dict(zip(spec['columns'],values));native=fields['id'];label=fields['name']
                    if not native or native!=native.strip() or not label:raise ValueError('usda-slice-required-native-fields')
                    native_ids.append(native)
                    member_rows.append({'partitionId':spec['table'],'nativeRecordId':native,
                        'sourcePath':name+'#/records/'+str(ordinal),
                        'kind':'NutrientDefinition' if spec['table']=='nutrient' else 'Unit',
                        'name':label,'language':'und','sourceFields':fields})
                if len(member_rows)!=spec['rows']:raise ValueError('usda-slice-count')
                if len(set(native_ids))!=len(native_ids):raise ValueError('usda-slice-duplicate-native-id')
                id_sha=native_id_digest(native_ids)
                if id_sha!=spec['nativeIdSha256']:raise ValueError('usda-slice-native-id-witness')
                rows.extend(member_rows)
                members.append({'table':spec['table'],'member':name,'rows':len(member_rows),
                    'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'crc32':info.CRC,
                    'crcValidatedByZipReader':True,'nativeIdSha256':id_sha,'columns':spec['columns'],
                    'compression':info.compress_type,'compressedBytes':info.compress_size,
                    'localHeaderOffset':info.header_offset})
        if (identity(os.fstat(stream.fileno()))!=observed or path.is_symlink() or
            identity(path.lstat())!=observed):raise ValueError('usda-slice-identity')
        source.guard()
        return rows,{'moduleVersion':VERSION,'archiveSha256':actual_sha,'archiveBytes':expected_bytes,
            'descriptorIdentityBefore':observed,'descriptorIdentityAfter':identity(os.fstat(stream.fileno())),
            'oneReadOnlyDescriptor':True,'sourceReadBytes':source.bytes,'sourceReadCalls':source.calls,
            'readBytesByStage':source.stage_bytes,'physicalDeviceIO':'Not inferred from application read count; OS/process observation recorded separately by caller.',
            'expandedSelectedBytes':expanded,'rows':len(rows),'members':members,
            'otherMemberBodiesParsed':0,'databaseOpens':0,'seconds':time.monotonic()-started,
            'state':'private-native-source-verified-not-semantically-reviewed-not-Gold'}

// JSONL uses literal LF, not Unicode text line separators inside JSON strings.
import {createReadStream} from 'node:fs';
import {createGunzip} from 'node:zlib';
import {StringDecoder} from 'node:string_decoder';
export async function* gzipLines(path){
 const file=createReadStream(path), unzip=createGunzip(), decoder=new StringDecoder('utf8');
 file.on('error',error=>unzip.destroy(error));file.pipe(unzip);
 let pending='';
 try{
  for await(const chunk of unzip){
   pending+=decoder.write(chunk);let offset=0,index;
   while((index=pending.indexOf('\n',offset))!==-1){const line=pending.slice(offset,index);if(line.trim())yield line;offset=index+1;}
   pending=pending.slice(offset);if(pending.length>64*1024*1024)throw Error('JSONL row exceeds local collection limit');
  }
  pending+=decoder.end();if(pending.trim())yield pending;
 }finally{file.destroy();unzip.destroy();}
}

import { createRemoteJWKSet, jwtVerify, type JWTVerifyGetKey } from 'jose';
import { z } from 'zod';
import { timingSafeEqual } from 'node:crypto';
import type { Env } from './config';
import { BridgeError } from './protocol';
export async function verifyOwnerJwt(token:string,env:Pick<Env,'ACCESS_TEAM_DOMAIN'|'ACCESS_AUD'|'OWNER_SUB'|'OWNER_EMAIL'>,key?:JWTVerifyGetKey, bootstrap=false){
  if(!/^[a-z0-9-]+\.cloudflareaccess\.com$/.test(env.ACCESS_TEAM_DOMAIN)||!env.ACCESS_AUD||(!bootstrap&&!env.OWNER_SUB)||!env.OWNER_EMAIL)throw new BridgeError('ACCESS_NOT_CONFIGURED',503);
  const issuer=`https://${env.ACCESS_TEAM_DOMAIN}`;
  const jwks=key??createRemoteJWKSet(new URL(`${issuer}/cdn-cgi/access/certs`),{timeoutDuration:5000});
  const {payload}=await jwtVerify(token,jwks,{issuer,audience:env.ACCESS_AUD,algorithms:['RS256'],requiredClaims:['exp','iat','sub','email'],clockTolerance:5});
  if((!bootstrap&&payload.sub!==env.OWNER_SUB)||typeof payload.email!=='string'||payload.email.toLowerCase()!==env.OWNER_EMAIL.toLowerCase()||payload.type!=='app')throw new BridgeError('OWNER_ONLY',403);
  return {sub:payload.sub!,email:env.OWNER_EMAIL.toLowerCase()};
}
export async function verifyPoller(header:string|null,expectedHash:string|undefined){
  if(!expectedHash||!/^Bearer [A-Za-z0-9_-]{43,256}$/.test(header??''))return false;
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(header!.slice(7)));
  const actual=new Uint8Array(digest),expected=Uint8Array.from(expectedHash.match(/../g)??[],x=>parseInt(x,16));
  if(expected.length!==actual.length)return false;
  // Both fixed-length hashes; no direct comparison of secret material.
  return timingSafeEqual(actual,expected);
}
export function oauthOwner(props:unknown,env:Pick<Env,'OWNER_SUB'|'OWNER_EMAIL'>){
  const p=z.object({sub:z.string(),email:z.string()}).safeParse(props);
  if(!p.success||!env.OWNER_SUB||!env.OWNER_EMAIL||p.data.sub!==env.OWNER_SUB||p.data.email!==env.OWNER_EMAIL.toLowerCase())throw new BridgeError('OWNER_ONLY',403);
}

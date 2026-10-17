import { z } from 'zod';
import type { OAuthHelpers } from '@cloudflare/workers-oauth-provider';
import { BridgeError, parseAllowlist } from './protocol';
export type Env = Cloudflare.Env & { POLLER_TOKEN_SHA256?: string; OAUTH_PROVIDER?: OAuthHelpers };
export function config(env:Env){
  if(env.ENABLED!=='true')throw new BridgeError('BRIDGE_DISABLED',503);
  const origin=new URL(env.PUBLIC_ORIGIN);
  if(origin.protocol!=='https:'||origin.origin!==env.PUBLIC_ORIGIN)throw new BridgeError('INVALID_PUBLIC_ORIGIN',503);
  if(!env.OWNER_SUB||!z.email().safeParse(env.OWNER_EMAIL).success)throw new BridgeError('OWNER_NOT_CONFIGURED',503);
  if(!/^[a-z0-9-]+\.cloudflareaccess\.com$/.test(env.ACCESS_TEAM_DOMAIN)||!env.ACCESS_AUD)throw new BridgeError('ACCESS_NOT_CONFIGURED',503);
  const sessions=parseAllowlist(env.ALLOWED_SESSION_IDS);
  const redirects=z.array(z.url()).min(1).max(8).parse(JSON.parse(env.ALLOWED_OAUTH_REDIRECT_URIS));
  if(redirects.some(url=>new URL(url).protocol!=='https:'))throw new BridgeError('INVALID_REDIRECT',503);
  if(!/^[a-f0-9]{64}$/.test(env.POLLER_TOKEN_SHA256??''))throw new BridgeError('POLLER_NOT_CONFIGURED',503);
  return {origin:origin.origin,hostname:origin.hostname,sessions,redirects};
}

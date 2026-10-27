import type {SourceIdentityReaderInput, Sha256} from './source-identity-contract.js';
export const HTTP_SCHEMA: 'offmenu-source-identity-http/1';
/** Throws unless the existing reader accepts the actual fixed inputs. No runtime start. */
export function createSourceIdentityHTTP(input: SourceIdentityReaderInput): Promise<Readonly<{
  selectionSha256: Sha256;
  handle(request: Request): Promise<Response | null>;
}>>;

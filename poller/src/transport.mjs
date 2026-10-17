import http from 'node:http';
import https from 'node:https';
import fs from 'node:fs';
import { MAX_BRIDGE_BYTES, MAX_LOCAL_BYTES, SafeError, HttpError, requireThat, validateCredentialHeaders, validateSnapshot, verifyAdapter } from './contracts.mjs';

export function readPrivateFile(path, maxBytes = 16 * 1024) {
  const fd = fs.openSync(path, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
  try {
    const stat = fs.fstatSync(fd);
    requireThat(stat.isFile() && stat.size <= maxBytes && (stat.mode & 0o077) === 0 &&
      (process.getuid === undefined || stat.uid === process.getuid()), 'PRIVATE_FILE_PERMISSIONS');
    const data = fs.readFileSync(fd, 'utf8');
    requireThat(Buffer.byteLength(data) <= maxBytes, 'PRIVATE_FILE_TOO_LARGE');
    return data;
  } finally { fs.closeSync(fd); }
}

export function requestJson(url, { method = 'GET', headers = {}, body, maxBytes = MAX_BRIDGE_BYTES, timeoutMs = 15000 } = {}) {
  return new Promise((resolve, reject) => {
    const encoded = body === undefined ? undefined : Buffer.from(JSON.stringify(body));
    if (encoded && encoded.length > maxBytes) return reject(new SafeError('OUTGOING_BODY_TOO_LARGE'));
    const client = url.protocol === 'https:' ? https : http;
    let ended = false;
    const fail = code => { if (!ended) { ended = true; reject(new SafeError(code)); } };
    const req = client.request(url, { method, headers: { accept: 'application/json', ...headers,
      ...(encoded ? { 'content-type': 'application/json', 'content-length': encoded.length } : {}) } }, response => {
      // Never forward either credential across a redirect, even to the same host.
      if (response.statusCode >= 300 && response.statusCode < 400) {
        response.resume(); fail(`HTTP_${response.statusCode}`); return;
      }
      const isError = response.statusCode < 200 || response.statusCode >= 300;
      const responseLimit = isError ? Math.min(maxBytes, 8192) : maxBytes;
      const chunks = []; let size = 0;
      response.on('data', chunk => {
        size += chunk.length;
        if (size > responseLimit) { response.destroy(); fail('RESPONSE_TOO_LARGE'); } else chunks.push(chunk);
      });
      response.on('error', () => fail('RESPONSE_ERROR'));
      response.on('end', () => {
        if (ended) return;
        const bytes = Buffer.concat(chunks);
        if (isError) {
          let serviceCode = null;
          if (String(response.headers['content-type'] ?? '').split(';')[0].trim().toLowerCase() === 'application/json') {
            try {
              const body = JSON.parse(bytes.toString('utf8'));
              if (body && typeof body === 'object' && !Array.isArray(body) && Object.keys(body).length === 1 &&
                ((response.statusCode === 404 && body.error === 'REQUEST_NOT_FOUND') ||
                 (response.statusCode === 403 && body.error === 'SESSION_NOT_ALLOWED'))) serviceCode = body.error;
            } catch { /* Unrecognized/auth/proxy error bodies never retire durable reports. */ }
          }
          ended = true; reject(new HttpError(response.statusCode, serviceCode)); return;
        }
        try {
          const result = bytes.length === 0 ? null : JSON.parse(bytes.toString('utf8'));
          ended = true; resolve(result);
        } catch { fail('RESPONSE_NOT_JSON'); }
      });
    });
    const timer = setTimeout(() => { req.destroy(); fail('REQUEST_TIMEOUT'); }, timeoutMs);
    timer.unref();
    req.on('close', () => clearTimeout(timer));
    req.on('error', () => fail('NETWORK_ERROR'));
    req.end(encoded);
  });
}

export class LocalClient {
  constructor(config, adapter, gatewayToken, { read = readPrivateFile, request = requestJson } = {}) {
    verifyAdapter(adapter);
    this.config = config; this.adapter = adapter; this.read = read; this.request = request;
    this.gatewayToken = gatewayToken; this.secrets = [gatewayToken];
  }
  headers() {
    const headers = validateCredentialHeaders(this.adapter.extractCredential(this.read(this.config.localCredentialFile)));
    requireThat(Object.values(headers).every(value => !value.includes(this.gatewayToken)), 'CREDENTIALS_MUST_BE_INDEPENDENT');
    this.secrets = [this.gatewayToken, ...Object.values(headers),
      ...Object.values(headers).flatMap(value => /^Bearer /i.test(value) ? [value.slice(7)] : []),
      ...(headers.cookie ? headers.cookie.split(';').map(part => part.slice(part.indexOf('=') + 1).trim()) : [])];
    return headers;
  }
  endpoint(sessionId, suffix = '') {
    requireThat(this.config.sessionIds.includes(sessionId), 'SESSION_NOT_ALLOWED');
    return new URL(`/api/thread/${sessionId}${suffix}`, this.config.localApiUrl);
  }
  async snapshot(sessionId) {
    const url = this.endpoint(sessionId);
    url.searchParams.set('projectPath', this.config.projectPath);
    const raw = await this.request(url, { headers: this.headers(), maxBytes: MAX_LOCAL_BYTES });
    const normalized = this.adapter.normalizeSnapshot(raw, { sessionId });
    return validateSnapshot(normalized, sessionId);
  }
  async queue(sessionId, text) {
    const url = this.endpoint(sessionId, '/queue');
    // This client has no start, resume, create, delete, or arbitrary API method.
    return this.request(url, { method: 'POST', headers: this.headers(), maxBytes: MAX_LOCAL_BYTES,
      body: { projectPath: this.config.projectPath, text, now: false } });
  }
}

export class GatewayClient {
  constructor(config, token, { request = requestJson } = {}) {
    requireThat(typeof token === 'string' && /^[A-Za-z0-9_-]{43,256}$/.test(token), 'POLLER_TOKEN_INVALID');
    this.origin = config.gatewayUrl; this.token = token; this.request = request;
  }
  send(path, body) {
    return this.request(new URL(path, this.origin), { method: 'POST', headers: { authorization: `Bearer ${this.token}` }, body });
  }
  poll() { return this.send('/bridge/poll', {}); }
  report(body) { return this.send('/bridge/report', body); }
  snapshot(body) { return this.send('/bridge/snapshot', body); }
}

// ../offmenu-source-barcode-facts-20261029/source/protocol-pins.mjs
var SOURCE_PINS = Object.freeze({
  "sourceManifestSha256": "8cd8abbf28f8fac11ccb73f336a91c7a5d90fbaff6ec1c864ec7b492f13da58e",
  "structuralManifestSha256": "83773291ac70931a110f60e872ae47a2bd470b5f397c709195dcf016c0bf0694",
  "consumerIndexSha256": "5e6d5c14a26515632a56aac2ff128a12baaa6ec7d030703c368cc8c297a4c1ad",
  "locatorManifestSha256": "3520dff24e7b96635fd3d8f8cfa60664d03d5bd65709b547059cee10b306e1a9",
  "locatorIndexSha256": "1691828696477efe932d6b3bfc1e20cbdc99ddf047da3e695067f40478e8c2cd",
  "publicBaseManifestSha256": "66b2ee6e016838453c59c1d1f6f05941d14c84a8084361ef099463a3a6471c05",
  "qualificationReceiptSha256": "9e60de075a9bf049e0348c666e4cc2cbe9edb07c6771bcab95649038dafd1226",
  "schemaSha256": "89ff701460e0c9c6e27c5d5ece7bd6868f26f55fc2aedd1d85c87b4408cf1f6c",
  "contractSha256": "b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa"
});

// ../offmenu-source-barcode-facts-20261029/source/strict-json.mjs
function strictJSON(text2, check = () => {
}, maxNodes = 2e5) {
  let i = 0, nodes = 0;
  const need5 = (ok) => {
    if (!ok) throw Error("invalid-json");
  };
  const ws = () => {
    while (i < text2.length && /[\t\r\n ]/.test(text2[i])) i++;
  };
  function string() {
    const start = i++;
    let escaped = false;
    while (i < text2.length) {
      const c = text2[i++];
      if (c === '"' && !escaped) {
        const value2 = JSON.parse(text2.slice(start, i));
        for (const cp of value2) need5(!(cp.codePointAt(0) >= 55296 && cp.codePointAt(0) <= 57343));
        return value2;
      }
      if (c === "\\" && !escaped) escaped = true;
      else escaped = false;
    }
    throw Error("unterminated-json-string");
  }
  function value(depth) {
    need5(depth <= 32 && ++nodes <= maxNodes);
    if ((nodes & 1023) === 0) check();
    ws();
    const c = text2[i];
    if (c === '"') return string();
    if (c === "{" || c === "[") {
      const object3 = c === "{", out = object3 ? /* @__PURE__ */ Object.create(null) : [];
      const keys = /* @__PURE__ */ new Set(), close = object3 ? "}" : "]";
      i++;
      ws();
      if (text2[i] === close) {
        i++;
        return out;
      }
      while (true) {
        ws();
        let key;
        if (object3) {
          need5(text2[i] === '"');
          key = string();
          need5(!keys.has(key));
          keys.add(key);
          ws();
          need5(text2[i++] === ":");
        }
        const v = value(depth + 1);
        if (object3) out[key] = v;
        else out.push(v);
        ws();
        const end = text2[i++];
        if (end === close) return out;
        need5(end === ",");
      }
    }
    for (const [literal, result2] of [["true", true], ["false", false], ["null", null]])
      if (text2.startsWith(literal, i)) {
        i += literal.length;
        return result2;
      }
    const match = /^-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?/.exec(text2.slice(i));
    need5(match);
    i += match[0].length;
    const n = Number(match[0]);
    need5(Number.isFinite(n) && (!Number.isInteger(n) || Number.isSafeInteger(n)));
    return n;
  }
  const result = value(0);
  ws();
  need5(i === text2.length);
  check();
  return result;
}

// ../offmenu-source-barcode-facts-20261029/source/stream-shard.mjs
async function scanShard(stream, {
  expectedBytes,
  expectedPrefix,
  expectedEntries,
  maxEntries,
  maxEntryBytes = 262144,
  maxEntryNodes = 8192,
  life,
  onEntry
}) {
  const fail = () => {
    throw Error("invalid-streamed-shard");
  };
  const reader = stream.getReader(), decoder = new TextDecoder("utf-8", { fatal: true }), encoder2 = new TextEncoder();
  let totalBytes = 0, done = false, state = "root", key = "", token = "", escaped = false, inString = false, depth = 0, count = 0;
  const keys = /* @__PURE__ */ new Set();
  const isSpace = (c) => c === " " || c === "\n" || c === "\r" || c === "	";
  async function consume(chunk) {
    for (let i = 0; i < chunk.length; i++) {
      const c = chunk[i];
      if (state === "entry") {
        token += c;
        if (token.length > maxEntryBytes) fail();
        if (inString) {
          if (escaped) escaped = false;
          else if (c === "\\") escaped = true;
          else if (c === '"') inString = false;
        } else if (c === '"') inString = true;
        else if (c === "{" || c === "[") depth++;
        else if (c === "}" || c === "]") depth--;
        if (depth === 0) {
          if (encoder2.encode(token).length > maxEntryBytes || ++count > maxEntries) fail();
          const entry = strictJSON(token, life.check, maxEntryNodes);
          token = "";
          await onEntry(entry);
          state = "after-entry";
          life.check();
        }
        continue;
      }
      if (state === "key-token" || state === "meta-token") {
        token += c;
        if (token.length > 256) fail();
        if (escaped) {
          escaped = false;
          continue;
        }
        if (c === "\\") {
          escaped = true;
          continue;
        }
        if (c === '"') {
          const value = strictJSON(token, life.check, 4);
          token = "";
          if (state === "key-token") {
            if (!["entries", "prefix", "schemaVersion"].includes(value) || keys.has(value)) fail();
            keys.add(value);
            key = value;
            state = "colon";
          } else {
            if (key === "prefix" ? value !== expectedPrefix : value !== "offmenu-source-barcode-index-shard/1") fail();
            state = "after-value";
          }
        }
        continue;
      }
      if (isSpace(c)) continue;
      switch (state) {
        case "root":
          if (c !== "{") fail();
          state = "key";
          break;
        case "key":
          if (c !== '"') fail();
          token = '"';
          escaped = false;
          state = "key-token";
          break;
        case "colon":
          if (c !== ":") fail();
          state = "value";
          break;
        case "value":
          if (key === "entries") {
            if (c !== "[") fail();
            state = "first-entry";
          } else {
            if (c !== '"') fail();
            token = '"';
            escaped = false;
            state = "meta-token";
          }
          break;
        case "first-entry":
        case "next-entry":
          if (c === "]" && state === "first-entry") {
            state = "after-value";
            break;
          }
          if (c !== "{") fail();
          token = "{";
          depth = 1;
          escaped = false;
          inString = false;
          state = "entry";
          break;
        case "after-entry":
          if (c === ",") state = "next-entry";
          else if (c === "]") state = "after-value";
          else fail();
          break;
        case "after-value":
          if (c === ",") state = "key";
          else if (c === "}") state = "done";
          else fail();
          break;
        default:
          fail();
      }
    }
  }
  try {
    while (true) {
      const part = await life.run(() => reader.read());
      if (part.done) {
        done = true;
        break;
      }
      if (!(part.value instanceof Uint8Array)) fail();
      totalBytes += part.value.byteLength;
      if (totalBytes > expectedBytes) fail();
      for (let offset = 0; offset < part.value.byteLength; offset += 65536) {
        await consume(decoder.decode(part.value.subarray(offset, offset + 65536), { stream: true }));
        life.check();
      }
    }
    await consume(decoder.decode());
    if (totalBytes !== expectedBytes || state !== "done" || keys.size !== 3 || count !== expectedEntries) fail();
    life.check();
    return { entries: count, decodedBytes: totalBytes };
  } finally {
    if (!done) void reader.cancel().catch(() => {
    });
    reader.releaseLock();
  }
}

// ../offmenu-source-barcode-facts-20261029/source/source-barcode-handler.mjs
var INDEX_RELEASE = "source-barcode-index-v1-20261029";
var ORIGIN = "https://offmenu-corpus.netlify.app";
var PREFIX = "/common-data/derived-releases/" + INDEX_RELEASE + "/";
var BASE = "/common-data/releases/common-corpus-expanded-20261014/";
var PUBLIC_BASE = Object.freeze({
  origin: ORIGIN,
  releaseId: "common-corpus-expanded-20261014",
  manifestPath: BASE + "manifest.json",
  manifestSha256: SOURCE_PINS.publicBaseManifestSha256,
  sourcePackageManifestPath: BASE + "bulk-food/source-package-manifest.json",
  sourcePackageManifestSha256: SOURCE_PINS.sourceManifestSha256,
  assetPrefix: BASE + "bulk-food/"
});
var RESOURCE_BOUNDS = Object.freeze({
  manifestBytes: 2 * 1024 * 1024,
  compressedBytes: 8 * 1024 * 1024,
  expandedBytes: 32 * 1024 * 1024,
  entries: 65536,
  jsonNodes: 2e5,
  responseBytes: 256 * 1024,
  cursorBytes: 32768,
  deadlineMs: 1e4
});
var SCHEMA = "offmenu-source-barcode-candidates/1";
var ENC = new TextEncoder();
var HEADERS = {
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer",
  "Permissions-Policy": "camera=(self), microphone=()",
  "Content-Security-Policy": "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self' https://offmenu-corpus.netlify.app; worker-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
  "Cache-Control": "no-store",
  "Content-Type": "application/json; charset=utf-8"
};
var need = (ok, code = "integrity") => {
  if (!ok) throw Error(code);
};
var object = (x) => x !== null && typeof x === "object" && !Array.isArray(x);
var integer = (x, min = 0, max = Number.MAX_SAFE_INTEGER) => Number.isSafeInteger(x) && x >= min && x <= max;
var sha = (x) => typeof x === "string" && /^[a-f0-9]{64}$/.test(x);
var text = (x, max = 4096) => typeof x === "string" && x.length > 0 && ENC.encode(x).length <= max;
var same = (a, b) => canonical(a) === canonical(b);
var fields = (x, keys) => object(x) && same(Object.keys(x).sort(), keys.slice().sort());
function canonical(x) {
  if (Array.isArray(x)) return "[" + x.map(canonical).join(",") + "]";
  if (object(x)) return "{" + Object.keys(x).sort().map((k) => JSON.stringify(k) + ":" + canonical(x[k])).join(",") + "}";
  return JSON.stringify(x);
}
async function digest(bytes) {
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), (b) => b.toString(16).padStart(2, "0")).join("");
}
function validateQuery(q) {
  need(fields(q, ["source", "release", "namespace", "lexical"]), "query");
  need(Object.values(q).every((v) => text(v, 16384)) && q.namespace === "barcode", "query");
  need(ENC.encode(canonical([q.source, q.release, q.namespace, q.lexical])).length <= 16384, "query");
  for (const v of Object.values(q)) for (const cp of v) need(!(cp.codePointAt(0) >= 55296 && cp.codePointAt(0) <= 57343), "query");
}
async function keySha(q) {
  validateQuery(q);
  return digest(ENC.encode(canonical([q.source, q.release, q.namespace, q.lexical])));
}
function unavailable(query) {
  return {
    schemaVersion: SCHEMA,
    query,
    status: "index-unavailable",
    candidateTotal: null,
    countKnown: false,
    complete: false,
    returnedCount: 0,
    truncated: null,
    candidates: [],
    nextCursor: null,
    referenceCoverageComplete: false,
    canonicalIdentityAsserted: false,
    automaticPlanningEligible: false,
    nutritionAggregationEligible: false
  };
}
function response(value, status = 200, extra = {}) {
  const body = JSON.stringify(value);
  need(ENC.encode(body).length <= RESOURCE_BOUNDS.responseBytes, "response-bound");
  return new Response(body, { status, headers: { ...HEADERS, ...extra } });
}
function selectionCopy(selection) {
  need(object(selection) && selection.manifestUrl === ORIGIN + PREFIX + "manifest.json" && sha(selection.manifestSha256) && selection.indexReleaseId === INDEX_RELEASE && same(selection.sourcePins, SOURCE_PINS) && same(selection.publicBase, PUBLIC_BASE), "selection");
  return { manifestUrl: selection.manifestUrl, manifestSha256: selection.manifestSha256, indexReleaseId: INDEX_RELEASE };
}
function validateManifest(m) {
  need(object(m) && m.schemaVersion === "offmenu-source-barcode-index/1" && m.indexReleaseId === INDEX_RELEASE && m.complete === true && same(m.sourcePins, SOURCE_PINS) && same(m.publicBase, PUBLIC_BASE) && m.candidateReferenceCap === 20 && m.canonicalIdentityAsserted === false && m.automaticPlanningEligible === false && m.nutritionAggregationEligible === false, "manifest");
  need(same(m.keyHash, {
    algorithm: "SHA256",
    input: "UTF-8 canonical JSON array [source,release,namespace,lexical]",
    canonicalJSON: "sorted object keys; no whitespace; ensure_ascii=false; finite JSON",
    normalization: "none",
    shardPrefixHexCharacters: 2
  }), "key-hash");
  const prefixes = Array.from({ length: 256 }, (_, i) => i.toString(16).padStart(2, "0"));
  need(object(m.shards) && same(Object.keys(m.shards).sort(), prefixes), "inventory");
  for (const prefix of prefixes) {
    const d = m.shards[prefix];
    need(object(d) && d.path === "shards/" + prefix + ".json.gz" && d.publicPath === PREFIX + d.path && sha(d.sha256) && integer(d.bytes, 1, 64 * 1024 * 1024) && integer(d.uncompressedBytes, 1, 256 * 1024 * 1024) && integer(d.indexedKeys), "descriptor");
  }
}
function validateRef(ref) {
  need(fields(ref, [
    "sourceResourceId",
    "asset",
    "identifierAssertion",
    "sourceAssertionStatus",
    "sourceAssertionStatusState",
    "citationRefs",
    "ingredientRefs",
    "nutrientRefs"
  ]) && text(ref.sourceResourceId), "reference");
  const a = ref.asset;
  need(fields(a, ["path", "sha256", "bytes", "packetOrdinal", "packetCount", "packetCanonicalSha256", "packetDigestState"]), "asset");
  need(text(a.path, 2048) && a.path.startsWith(PUBLIC_BASE.assetPrefix) && !/[\\%?#\x00-\x20]/.test(a.path) && a.path.split("/").slice(1).every((x) => x && x !== "." && x !== "..") && new URL(a.path, ORIGIN).pathname === a.path, "asset-path");
  need(sha(a.sha256) && integer(a.bytes, 1) && integer(a.packetCount, 1) && integer(a.packetOrdinal, 0, a.packetCount - 1) && a.packetCanonicalSha256 === null && a.packetDigestState === "not-retained-in-selected-product-locator-index", "asset-locator");
  const assertion = ref.identifierAssertion;
  need(fields(assertion, ["id", "canonicalSha256", "matchingAssertionCount", "referencesTruncated"]) && text(assertion.id) && sha(assertion.canonicalSha256) && integer(assertion.matchingAssertionCount, 1) && assertion.referencesTruncated === assertion.matchingAssertionCount > 1, "assertion");
  need(ref.sourceAssertionStatus === null && ref.sourceAssertionStatusState === "resolve-original-public-assertion" && ["citationRefs", "ingredientRefs", "nutrientRefs"].every((k) => ref[k] === null), "evidence");
}
function cursorDecode(cursor, selection, query, limit) {
  if (cursor === null) return 0;
  need(text(cursor, RESOURCE_BOUNDS.cursorBytes) && /^[A-Za-z0-9_-]+$/.test(cursor), "cursor");
  const bytes = Uint8Array.from(atob(cursor.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - cursor.length % 4) % 4)), (c2) => c2.charCodeAt(0));
  const c = strictJSON(new TextDecoder("utf-8", { fatal: true }).decode(bytes), () => {
  }, 100);
  need(fields(c, ["manifestSha256", "query", "limit", "offset"]) && c.manifestSha256 === selection.manifestSha256 && same(c.query, query) && c.limit === limit && integer(c.offset, 0, 20), "cursor-binding");
  need(cursorEncode(c) === cursor, "cursor-canonical");
  return c.offset;
}
function cursorEncode(c) {
  return btoa(Array.from(ENC.encode(canonical(c)), (b) => String.fromCharCode(b)).join("")).replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_");
}
function lifetime(request) {
  const controller = new AbortController(), deadline = Date.now() + RESOURCE_BOUNDS.deadlineMs;
  const abort = () => controller.abort();
  request.signal.addEventListener("abort", abort, { once: true });
  if (request.signal.aborted) abort();
  const timer = setTimeout(abort, RESOURCE_BOUNDS.deadlineMs);
  const check = () => need(!controller.signal.aborted && Date.now() <= deadline, "deadline");
  async function run(call) {
    check();
    let listener;
    try {
      return await Promise.race([Promise.resolve().then(call), new Promise((_, reject) => {
        listener = () => reject(Error("cancelled-or-deadline"));
        controller.signal.addEventListener("abort", listener, { once: true });
        if (controller.signal.aborted) listener();
      })]);
    } finally {
      if (listener) controller.signal.removeEventListener("abort", listener);
    }
  }
  return { stage: "request", signal: controller.signal, check, run, close: () => {
    controller.abort();
    clearTimeout(timer);
    request.signal.removeEventListener("abort", abort);
  } };
}
async function boundedBytes(stream, max, life, exact2 = null) {
  need(stream && typeof stream.getReader === "function", "stream");
  const reader = stream.getReader();
  const chunks = [];
  let size = 0, done = false;
  try {
    while (true) {
      const part = await life.run(() => reader.read());
      if (part.done) {
        done = true;
        break;
      }
      need(part.value instanceof Uint8Array, "stream-chunk");
      size += part.value.byteLength;
      need(size <= max, "byte-bound");
      chunks.push(part.value);
    }
    need(exact2 === null || size === exact2, "byte-count");
    const joined = new Uint8Array(size);
    let offset = 0;
    for (const c of chunks) {
      joined.set(c, offset);
      offset += c.byteLength;
    }
    return joined;
  } finally {
    if (!done) void reader.cancel().catch(() => {
    });
    reader.releaseLock();
  }
}
async function fetchBytes(url, max, life, fetchImpl, exact2 = null) {
  const res = await life.run(() => fetchImpl(url, {
    method: "GET",
    redirect: "manual",
    credentials: "omit",
    cache: "no-store",
    headers: { Accept: "application/json, application/gzip", "Accept-Encoding": "identity" },
    signal: life.signal
  }));
  let consumed = false;
  try {
    need(res && res.status === 200 && !res.redirected && (!res.url || res.url === url), "http");
    need(!res.headers.get("content-encoding") || res.headers.get("content-encoding") === "identity", "http-encoding");
    const len = res.headers.get("content-length");
    if (len !== null) need(/^\d+$/.test(len) && Number(len) <= max && (exact2 === null || Number(len) === exact2), "http-size");
    const result = await boundedBytes(res.body, max, life, exact2);
    consumed = true;
    return result;
  } finally {
    if (!consumed && res?.body && !res.body.locked) void res.body.cancel().catch(() => {
    });
  }
}
async function lookup(query, limit, cursor, selection, fetchImpl, life) {
  life.stage = "cursor";
  const offset = cursorDecode(cursor, selection, query, limit);
  life.stage = "manifest-fetch";
  const manifestBytes = await fetchBytes(selection.manifestUrl, RESOURCE_BOUNDS.manifestBytes, life, fetchImpl);
  life.stage = "manifest-sha";
  need(await life.run(() => digest(manifestBytes)) === selection.manifestSha256, "manifest-sha");
  const decode = (bytes2) => strictJSON(new TextDecoder("utf-8", { fatal: true }).decode(bytes2), life.check, RESOURCE_BOUNDS.jsonNodes);
  life.stage = "manifest-parse";
  const m = decode(manifestBytes);
  validateManifest(m);
  life.stage = "key-hash";
  const hash2 = await life.run(() => keySha(query)), prefix = hash2.slice(0, 2), d = m.shards[prefix];
  life.stage = "resource-bounds";
  need(d.bytes <= RESOURCE_BOUNDS.compressedBytes && d.uncompressedBytes <= RESOURCE_BOUNDS.expandedBytes && d.indexedKeys <= RESOURCE_BOUNDS.entries, "worker-resource-bound");
  life.stage = "shard-fetch";
  const bytes = await fetchBytes(ORIGIN + d.publicPath, d.bytes, life, fetchImpl, d.bytes);
  life.stage = "shard-sha";
  need(await life.run(() => digest(bytes)) === d.sha256, "shard-sha");
  life.stage = "shard-stream";
  let compressedOffset = 0;
  const input = new ReadableStream({ pull(controller) {
    if (compressedOffset === bytes.length) {
      controller.close();
      return;
    }
    const end = Math.min(bytes.length, compressedOffset + 65536);
    controller.enqueue(bytes.subarray(compressedOffset, end));
    compressedOffset = end;
  } });
  let previous = "", entry = null;
  await scanShard(input.pipeThrough(new DecompressionStream("gzip")), {
    expectedBytes: d.uncompressedBytes,
    expectedPrefix: prefix,
    expectedEntries: d.indexedKeys,
    maxEntries: RESOURCE_BOUNDS.entries,
    life,
    onEntry: async (e) => {
      life.check();
      validateQuery(e.key);
      const h = await life.run(() => keySha(e.key));
      need(h === e.keySha256 && h.startsWith(prefix) && h > previous, "key-binding");
      previous = h;
      need(integer(e.candidateTotal, 1) && Array.isArray(e.candidates) && e.candidates.length === Math.min(e.candidateTotal, 20) && e.returnedCount === e.candidates.length && e.truncated === e.candidateTotal > e.candidates.length, "candidate-count");
      const seen = /* @__PURE__ */ new Set();
      for (const ref of e.candidates) {
        validateRef(ref);
        need(!seen.has(ref.sourceResourceId), "duplicate-resource");
        seen.add(ref.sourceResourceId);
      }
      if (h === hash2) {
        need(same(e.key, query) && entry === null, "exact-tuple");
        entry = e;
      }
    }
  });
  life.stage = "response";
  const refs = entry?.candidates || [], total = entry?.candidateTotal || 0;
  need(offset <= refs.length, "cursor-offset");
  const page = refs.slice(offset, offset + limit), next = offset + page.length;
  return {
    ...unavailable(query),
    status: total === 0 ? "source-key-not-found" : total > 1 ? "ambiguous-source-key" : "source-scoped-candidates",
    candidateTotal: total,
    countKnown: true,
    complete: true,
    returnedCount: page.length,
    truncated: total > page.length,
    candidates: page,
    nextCursor: next < refs.length ? cursorEncode({ manifestSha256: selection.manifestSha256, query, limit, offset: next }) : null,
    referenceCoverageComplete: refs.length === total,
    manifestSha256: selection.manifestSha256,
    indexReleaseId: INDEX_RELEASE,
    sourcePins: m.sourcePins,
    publicBase: m.publicBase
  };
}
function createSourceBarcodeHandler({ selection, fetchImpl = (...args) => globalThis.fetch(...args), onDiagnostic } = {}) {
  let pinned = null;
  try {
    pinned = selectionCopy(selection);
  } catch {
  }
  return async function handle(request) {
    const url = new URL(request.url);
    if (url.pathname !== "/api/corpus/source-barcode") return null;
    if (request.method !== "GET") return response(unavailable(null), 405, { Allow: "GET" });
    let query = null, limit, cursor;
    try {
      need(ENC.encode(url.search).length <= 65536, "query-size");
      const allowed = ["source", "release", "namespace", "value", "limit", "cursor"];
      for (const k of url.searchParams.keys()) need(allowed.includes(k) && url.searchParams.getAll(k).length === 1, "query-fields");
      query = { source: url.searchParams.get("source"), release: url.searchParams.get("release"), namespace: url.searchParams.get("namespace"), lexical: url.searchParams.get("value") };
      validateQuery(query);
      const raw = url.searchParams.get("limit");
      need(raw === null || /^(?:[1-9]|1[0-9]|20)$/.test(raw), "limit");
      limit = raw === null ? 20 : Number(raw);
      cursor = url.searchParams.get("cursor");
      need(cursor === null || text(cursor, RESOURCE_BOUNDS.cursorBytes), "cursor");
    } catch {
      return response(unavailable(null), 400);
    }
    const report = (stage, error) => {
      if (typeof onDiagnostic !== "function") return;
      const codes = /* @__PURE__ */ new Set([
        "selection",
        "http",
        "http-encoding",
        "http-size",
        "stream",
        "stream-chunk",
        "byte-bound",
        "byte-count",
        "manifest-sha",
        "manifest",
        "key-hash",
        "inventory",
        "descriptor",
        "worker-resource-bound",
        "shard-sha",
        "invalid-json",
        "unterminated-json-string",
        "invalid-streamed-shard",
        "key-binding",
        "candidate-count",
        "duplicate-resource",
        "reference",
        "asset",
        "asset-path",
        "asset-locator",
        "assertion",
        "evidence",
        "exact-tuple",
        "cursor",
        "cursor-binding",
        "cursor-canonical",
        "cursor-offset",
        "response-bound",
        "deadline",
        "cancelled-or-deadline"
      ]);
      const names = /* @__PURE__ */ new Set(["Error", "TypeError", "RangeError", "AbortError", "DataError", "OperationError"]);
      try {
        onDiagnostic(Object.freeze({
          schema: "offmenu-source-barcode-internal-diagnostic/1",
          stage,
          code: codes.has(error?.message) ? error.message : "runtime-operation-failed",
          errorType: names.has(error?.name) ? error.name : "UnknownError"
        }));
      } catch {
      }
    };
    if (!pinned || typeof fetchImpl !== "function") {
      report("selection", Error("selection"));
      return response(unavailable(query), 503);
    }
    const life = lifetime(request);
    try {
      return response(await lookup(query, limit, cursor, pinned, fetchImpl, life));
    } catch (error) {
      report(life.stage, error);
      return response(unavailable(query), 503);
    } finally {
      life.close();
    }
  };
}

// ../offmenu-source-barcode-facts-20261029/source/reviewed-hydration/source-barcode-client.mjs
var SOURCE_BARCODE_PINS = Object.freeze({
  sourceManifestSha256: "8cd8abbf28f8fac11ccb73f336a91c7a5d90fbaff6ec1c864ec7b492f13da58e",
  structuralManifestSha256: "83773291ac70931a110f60e872ae47a2bd470b5f397c709195dcf016c0bf0694",
  consumerIndexSha256: "5e6d5c14a26515632a56aac2ff128a12baaa6ec7d030703c368cc8c297a4c1ad",
  locatorManifestSha256: "3520dff24e7b96635fd3d8f8cfa60664d03d5bd65709b547059cee10b306e1a9",
  locatorIndexSha256: "1691828696477efe932d6b3bfc1e20cbdc99ddf047da3e695067f40478e8c2cd",
  publicBaseManifestSha256: "66b2ee6e016838453c59c1d1f6f05941d14c84a8084361ef099463a3a6471c05",
  qualificationReceiptSha256: "9e60de075a9bf049e0348c666e4cc2cbe9edb07c6771bcab95649038dafd1226",
  schemaSha256: "89ff701460e0c9c6e27c5d5ece7bd6868f26f55fc2aedd1d85c87b4408cf1f6c",
  contractSha256: "b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa"
});
var PREFIX2 = "/common-data/releases/common-corpus-expanded-20261014/";
var SOURCE_BARCODE_PUBLIC_BASE = Object.freeze({ origin: "https://offmenu-corpus.netlify.app", releaseId: "common-corpus-expanded-20261014", manifestPath: PREFIX2 + "manifest.json", manifestSha256: SOURCE_BARCODE_PINS.publicBaseManifestSha256, sourcePackageManifestPath: PREFIX2 + "bulk-food/source-package-manifest.json", sourcePackageManifestSha256: SOURCE_BARCODE_PINS.sourceManifestSha256, assetPrefix: PREFIX2 + "bulk-food/" });
var SHARED = ["schemaVersion", "query", "status", "candidateTotal", "countKnown", "complete", "returnedCount", "truncated", "candidates", "nextCursor", "referenceCoverageComplete", "canonicalIdentityAsserted", "automaticPlanningEligible", "nutritionAggregationEligible"];
var SUCCESS = [...SHARED, "manifestSha256", "indexReleaseId", "sourcePins", "publicBase"];
var object2 = (x) => x !== null && typeof x === "object" && !Array.isArray(x);
var exact = (x, keys) => object2(x) && Object.keys(x).length === keys.length && keys.every((k) => Object.hasOwn(x, k));
var nonempty = (x) => typeof x === "string" && x.length > 0;
var integer2 = (x) => Number.isSafeInteger(x) && x >= 0;
var sha2 = (x) => typeof x === "string" && /^[a-f0-9]{64}$/.test(x);
var need2 = (ok, reason = "SOURCE_BARCODE_RESPONSE_MISMATCH") => {
  if (!ok) throw Error(reason);
};
var clone = (x) => structuredClone(x);
function parseSourceBarcodeJSON(text2) {
  need2(typeof text2 === "string" && new TextEncoder().encode(text2).length <= 2 * 1024 * 1024, "SOURCE_BARCODE_RESPONSE_BOUND");
  const value = JSON.parse(text2);
  let p = 0;
  const space = () => {
    while (/[\x20\t\n\r]/.test(text2[p] || "x")) p++;
  };
  function string() {
    const start = p++;
    while (p < text2.length) {
      const c = text2[p++];
      if (c === "\\") p++;
      else if (c === '"') return JSON.parse(text2.slice(start, p));
    }
    throw Error("SOURCE_BARCODE_JSON");
  }
  function walk(depth = 0) {
    need2(depth <= 40, "SOURCE_BARCODE_JSON_DEPTH");
    space();
    if (text2[p] === "{") {
      p++;
      space();
      const keys = /* @__PURE__ */ new Set();
      if (text2[p] === "}") {
        p++;
        return;
      }
      for (; ; ) {
        space();
        const key = string();
        need2(!keys.has(key), "SOURCE_BARCODE_DUPLICATE_JSON_KEY");
        keys.add(key);
        space();
        p++;
        walk(depth + 1);
        space();
        if (text2[p++] === "}") break;
      }
    } else if (text2[p] === "[") {
      p++;
      space();
      if (text2[p] === "]") {
        p++;
        return;
      }
      for (; ; ) {
        walk(depth + 1);
        space();
        if (text2[p++] === "]") break;
      }
    } else if (text2[p] === '"') string();
    else {
      const start = p;
      while (p < text2.length && !/[\x20\t\n\r,}\]]/.test(text2[p])) p++;
      const n = JSON.parse(text2.slice(start, p));
      need2(typeof n !== "number" || Number.isFinite(n), "SOURCE_BARCODE_NONFINITE_JSON");
    }
  }
  walk();
  space();
  need2(p === text2.length);
  return value;
}
function reference(ref, base) {
  need2(exact(ref, ["sourceResourceId", "asset", "identifierAssertion", "sourceAssertionStatus", "sourceAssertionStatusState", "citationRefs", "ingredientRefs", "nutrientRefs"]) && nonempty(ref.sourceResourceId));
  const a = ref.asset;
  need2(exact(a, ["path", "sha256", "bytes", "packetOrdinal", "packetCount", "packetCanonicalSha256", "packetDigestState"]));
  need2(nonempty(a.path) && a.path.startsWith(base.assetPrefix) && !a.path.split("/").slice(1).some((p) => !p || p === "." || p === ".."));
  const url = new URL(a.path, base.origin);
  need2(url.origin === base.origin && url.pathname === a.path && !url.search && !url.hash);
  need2(sha2(a.sha256) && integer2(a.bytes) && a.bytes > 0 && integer2(a.packetOrdinal) && integer2(a.packetCount) && a.packetOrdinal < a.packetCount);
  need2(a.packetCanonicalSha256 === null && a.packetDigestState === "not-retained-in-selected-product-locator-index");
  const i = ref.identifierAssertion;
  need2(exact(i, ["id", "canonicalSha256", "matchingAssertionCount", "referencesTruncated"]) && nonempty(i.id) && sha2(i.canonicalSha256) && integer2(i.matchingAssertionCount) && i.matchingAssertionCount >= 1 && i.referencesTruncated === i.matchingAssertionCount > 1);
  need2(ref.sourceAssertionStatus === null && ref.sourceAssertionStatusState === "resolve-original-public-assertion" && ref.citationRefs === null && ref.ingredientRefs === null && ref.nutrientRefs === null);
  return clone(ref);
}
var validateSourceBarcodeReference = (ref, base = SOURCE_BARCODE_PUBLIC_BASE) => reference(ref, base);

// ../offmenu-source-barcode-facts-20261029/source/reviewed-hydration/source-barcode-hydrator.mjs
var P = "urn:offmenu:property:";
var need3 = (ok) => {
  if (!ok) throw Error("SOURCE_DETAILS_UNAVAILABLE");
};
var canonical2 = (v) => Array.isArray(v) ? "[" + v.map(canonical2).join(",") + "]" : v !== null && typeof v === "object" ? "{" + Object.keys(v).sort().map((k) => JSON.stringify(k) + ":" + canonical2(v[k])).join(",") + "}" : JSON.stringify(v);
var hash = async (bytes) => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), (b) => b.toString(16).padStart(2, "0")).join("");
var HYDRATION_LIMITS = Object.freeze({ compressedBytes: 8 * 1024 * 1024, expandedBytes: 32 * 1024 * 1024, packetBytes: 2 * 1024 * 1024, packets: 1e4, rows: 3e4, timeoutMs: 15e3, displayCharacters: 65536 });
async function projectOriginalPacket(graph, c, signal = new AbortController().signal) {
  need3(graph?.schemaVersion === "offmenu-common/1");
  const maps = {};
  let count = 0;
  for (const key of ["resources", "assertions", "relations", "citations", "translations"]) {
    need3(Array.isArray(graph[key]));
    count += graph[key].length;
    need3(count <= HYDRATION_LIMITS.rows);
    maps[key] = /* @__PURE__ */ new Map();
    for (const row of graph[key]) {
      need3(typeof row.id === "string" && row.id && !maps[key].has(row.id));
      maps[key].set(row.id, row);
    }
  }
  const cite = (id) => {
    const row = maps.citations.get(id);
    need3(row?.scope?.visibility === "public" && row.sourceId === c.query.source && row.revisionId === c.query.release && typeof row.license === "string" && row.license.length > 0 && typeof row.attribution === "string" && row.attribution.length > 0);
    return row;
  };
  const cited = (ids) => {
    need3(Array.isArray(ids) && ids.length > 0);
    return ids.map(cite);
  };
  const publicRow = (row) => {
    need3(row?.scope?.visibility === "public");
    cited(row.citationIds);
    need3(row.status !== "superseded");
    return row;
  };
  const resource = publicRow(maps.resources.get(c.reference.sourceResourceId));
  const assertion = publicRow(maps.assertions.get(c.reference.identifierAssertion.id));
  need3(assertion.subjectId === resource.id && assertion.propertyId === P + "sourceIdentifier" && ["source-asserted", "candidate", "editor-authored", "reviewed", "verified"].includes(assertion.status));
  need3(await hash(new TextEncoder().encode(canonical2(assertion))) === c.reference.identifierAssertion.canonicalSha256);
  const f = assertion.value?.fields;
  need3(assertion.value?.kind === "structure" && f?.system?.kind === "identifier" && f.system.value === c.query.namespace && f.value?.kind === "identifier" && f.value.value === c.query.lexical);
  let budget = HYDRATION_LIMITS.displayCharacters;
  const retainedCitations = /* @__PURE__ */ new Map();
  function evidence(ids) {
    for (const row of cited(ids)) retainedCitations.set(row.id, { id: row.id, sourceId: row.sourceId, revisionId: row.revisionId, originalRecordId: row.originalRecordId ?? null, license: row.license, attribution: row.attribution, originalUrl: row.originalUrl ?? null, rightsEvidenceUrl: row.rightsEvidenceUrl ?? null });
  }
  function text2(s) {
    need3(typeof s === "string");
    budget -= s.length;
    need3(budget >= 0 && !signal.aborted);
    return s;
  }
  async function value(v, depth = 0) {
    need3(depth <= 30 && v && typeof v === "object" && !signal.aborted);
    switch (v.kind) {
      case "text":
        need3(v.status !== "superseded");
        evidence(v.citationIds);
        need3(typeof v.value === "string" && await hash(new TextEncoder().encode(v.value)) === v.sourceTextSha256);
        return text2(v.value);
      case "null":
        need3(v.value === null);
        return "Unknown";
      case "number":
        need3(typeof v.value === "number" && Number.isFinite(v.value));
        return String(v.value);
      case "boolean":
        need3(typeof v.value === "boolean");
        return String(v.value);
      case "identifier":
      case "uri":
      case "expression":
      case "date":
      case "datetime":
        return text2(v.value);
      case "reference":
        return text2(v.id) + " (source reference; unresolved)";
      case "list":
        need3(Array.isArray(v.items));
        return (await Promise.all(v.items.map((i) => value(i, depth + 1)))).join(" \xB7 ");
      case "structure":
        need3(v.fields && typeof v.fields === "object" && !Array.isArray(v.fields));
        return (await Promise.all(Object.entries(v.fields).map(async ([k, item]) => text2(k) + ": " + await value(item, depth + 1)))).join(" \xB7 ");
      case "quantity": {
        need3(v.value === null || typeof v.value === "number" && Number.isFinite(v.value));
        let out = (v.value === null ? "Unknown" : String(v.value)) + " " + text2(v.sourceUnit || v.unitId || "Unknown unit");
        if (v.basis) out += " per " + await value(v.basis, depth + 1);
        if (v.qualifiers) out += "; qualifiers: " + text2(JSON.stringify(v.qualifiers));
        if (v.sourceValue !== void 0) out += "; original value: " + text2(JSON.stringify(v.sourceValue));
        if (v.sourceNotation) out += "; notation: " + await value(v.sourceNotation, depth + 1);
        return out;
      }
      default:
        throw Error("SOURCE_DETAILS_UNAVAILABLE");
    }
  }
  evidence(resource.citationIds);
  evidence(assertion.citationIds);
  const names = [];
  for (const name of resource.names || []) names.push(await value(name));
  const facts = [];
  for (const row of graph.assertions.filter((r) => r.subjectId === resource.id)) {
    publicRow(row);
    evidence(row.citationIds);
    if (!["sourceFields", "nutrientObservation", "sourceNutrientMetadata"].some((k) => row.propertyId === P + k)) continue;
    if (row.propertyId === P + "sourceFields") {
      need3(row.value?.kind === "structure" && row.value.fields);
      for (const [key, v] of Object.entries(row.value.fields)) facts.push({ label: text2(key), text: await value(v), assertionId: row.id, status: row.status, sourcePath: row.sourcePath ?? null, citationIds: [...row.citationIds] });
    } else facts.push({ label: row.sourcePath || row.propertyId.slice(P.length), text: await value(row.value), assertionId: row.id, status: row.status, sourcePath: row.sourcePath ?? null, citationIds: [...row.citationIds] });
  }
  const unresolved = [];
  for (const row of graph.relations.filter((r) => r.subjectId === resource.id)) {
    publicRow(row);
    evidence(row.citationIds);
    unresolved.push({ predicateId: row.predicateId, objectId: row.objectId, status: row.status });
  }
  need3(!signal.aborted);
  return {
    name: names[0] ?? null,
    names,
    resourceType: resource.type,
    identityStatus: resource.identityStatus,
    identifierStatus: assertion.status,
    facts,
    citations: [...retainedCitations.values()],
    unresolvedRelations: unresolved,
    canonicalIdentityAsserted: false,
    automaticPlanningEligible: false,
    nutritionAggregationEligible: false
  };
}

// ../offmenu-source-barcode-facts-20261029/source/source-barcode-facts-handler.mjs
var FACTS_BOUNDS = Object.freeze({
  compressedBytes: 8 * 1024 * 1024,
  expandedBytes: 32 * 1024 * 1024,
  packetBytes: 2 * 1024 * 1024,
  packets: 1e4,
  responseBytes: 2 * 1024 * 1024,
  timeoutMs: 12e4,
  decodeWindow: 65536
});
var need4 = (ok) => {
  if (!ok) throw Error("facts-unavailable");
};
var encoder = new TextEncoder();
var sha3 = async (bytes) => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), (b) => b.toString(16).padStart(2, "0")).join("");
function lifetime2(request) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  request.signal.addEventListener("abort", abort, { once: true });
  if (request.signal.aborted) abort();
  const timer = setTimeout(abort, FACTS_BOUNDS.timeoutMs);
  async function run(call) {
    need4(!controller.signal.aborted);
    let listener;
    try {
      return await Promise.race([Promise.resolve().then(call), new Promise((_, reject) => {
        listener = () => reject(Error("facts-unavailable"));
        controller.signal.addEventListener("abort", listener, { once: true });
        if (controller.signal.aborted) listener();
      })]);
    } finally {
      if (listener) controller.signal.removeEventListener("abort", listener);
    }
  }
  return { signal: controller.signal, run, close() {
    controller.abort();
    clearTimeout(timer);
    request.signal.removeEventListener("abort", abort);
  } };
}
async function compressedBytes(stream, expected, life) {
  need4(stream?.getReader);
  const reader = stream.getReader(), parts = [];
  let size = 0, done = false;
  try {
    for (; ; ) {
      const p = await life.run(() => reader.read());
      if (p.done) {
        done = true;
        break;
      }
      need4(p.value instanceof Uint8Array);
      size += p.value.byteLength;
      need4(size <= expected);
      parts.push(p.value);
    }
    need4(size === expected);
    const out = new Uint8Array(size);
    let offset = 0;
    for (const p of parts) {
      out.set(p, offset);
      offset += p.byteLength;
    }
    return out;
  } finally {
    if (!done) void reader.cancel().catch(() => {
    });
    reader.releaseLock();
  }
}
async function selectOriginalPacket(stream, asset, life) {
  need4(stream?.getReader);
  const reader = stream.getReader(), decoder = new TextDecoder("utf-8", { fatal: true });
  let expanded = 0, ordinal = 0, selectedBytes = 0, lastNewline = false, done = false;
  const selected = [];
  function consume(text2) {
    if (!text2.length) return;
    lastNewline = text2.endsWith("\n");
    let start = 0;
    for (; ; ) {
      const newline = text2.indexOf("\n", start), end = newline < 0 ? text2.length : newline;
      if (ordinal === asset.packetOrdinal) {
        const piece = text2.slice(start, end);
        selectedBytes += encoder.encode(piece).length;
        need4(selectedBytes <= FACTS_BOUNDS.packetBytes);
        selected.push(piece);
      }
      if (newline < 0) break;
      ordinal++;
      need4(ordinal <= asset.packetCount && ordinal <= FACTS_BOUNDS.packets);
      start = newline + 1;
      if (start === text2.length) break;
    }
  }
  try {
    for (; ; ) {
      const p = await life.run(() => reader.read());
      if (p.done) {
        done = true;
        break;
      }
      need4(p.value instanceof Uint8Array);
      expanded += p.value.byteLength;
      need4(expanded <= FACTS_BOUNDS.expandedBytes);
      for (let offset = 0; offset < p.value.length; offset += FACTS_BOUNDS.decodeWindow)
        consume(decoder.decode(p.value.subarray(offset, offset + FACTS_BOUNDS.decodeWindow), { stream: true }));
    }
    consume(decoder.decode());
    need4(lastNewline && ordinal === asset.packetCount && selectedBytes > 0 && !life.signal.aborted);
    return parseSourceBarcodeJSON(selected.join(""));
  } finally {
    if (!done) void reader.cancel().catch(() => {
    });
    reader.releaseLock();
  }
}
async function hydrateOriginal(candidateLookup, request, fetchImpl) {
  const reference2 = validateSourceBarcodeReference(candidateLookup.candidates[0], PUBLIC_BASE), a = reference2.asset;
  need4(a.bytes <= FACTS_BOUNDS.compressedBytes && a.packetCount <= FACTS_BOUNDS.packets && a.path.endsWith(".jsonl.gz"));
  const url = new URL(a.path, ORIGIN);
  need4(url.origin === ORIGIN && url.pathname === a.path && !url.search && !url.hash && !url.username && !url.password);
  const life = lifetime2(request);
  let response2;
  try {
    response2 = await life.run(() => fetchImpl(url.href, {
      method: "GET",
      redirect: "manual",
      credentials: "omit",
      cache: "no-store",
      headers: { Accept: "application/gzip", "Accept-Encoding": "identity" },
      signal: life.signal
    }));
    need4(response2.status === 200 && !response2.redirected && (!response2.url || response2.url === url.href));
    need4(!response2.headers.get("content-encoding") || response2.headers.get("content-encoding") === "identity");
    const declared = response2.headers.get("content-length");
    if (declared !== null) need4(/^\d+$/.test(declared) && Number(declared) === a.bytes);
    const bytes = await compressedBytes(response2.body, a.bytes, life);
    need4(await life.run(() => sha3(bytes)) === a.sha256);
    let offset = 0;
    const input = new ReadableStream({ pull(c) {
      if (offset === bytes.length) {
        c.close();
        return;
      }
      const end = Math.min(bytes.length, offset + 65536);
      c.enqueue(bytes.subarray(offset, end));
      offset = end;
    } });
    const graph = await selectOriginalPacket(input.pipeThrough(new DecompressionStream("gzip")), a, life);
    const context = { query: candidateLookup.query, reference: reference2 };
    const projection = await life.run(() => projectOriginalPacket(graph, context, life.signal));
    need4(!life.signal.aborted);
    return projection;
  } finally {
    life.close();
    if (response2?.body && !response2.body.locked) void response2.body.cancel().catch(() => {
    });
  }
}
function factsEnvelope(candidateLookup, factsStatus, originalFacts = null) {
  return {
    schemaVersion: "offmenu-source-barcode-facts/1",
    candidateLookup,
    factsStatus,
    originalFacts,
    canonicalIdentityAsserted: false,
    automaticPlanningEligible: false,
    nutritionAggregationEligible: false
  };
}
function respond(envelope, base, status = base.status) {
  const body = JSON.stringify(envelope);
  need4(encoder.encode(body).length <= FACTS_BOUNDS.responseBytes);
  const headers = new Headers(base.headers);
  headers.set("Content-Type", "application/json; charset=utf-8");
  headers.set("Cache-Control", "no-store");
  return new Response(body, { status, headers });
}
function createSourceBarcodeHandler2({ selection, fetchImpl = (...args) => globalThis.fetch(...args), onDiagnostic } = {}) {
  const candidates = createSourceBarcodeHandler({ selection, fetchImpl, onDiagnostic });
  return async function handle(request) {
    const url = new URL(request.url);
    if (url.pathname !== "/api/corpus/source-barcode" || !url.searchParams.has("include")) return candidates(request);
    if (url.searchParams.getAll("include").length !== 1 || url.searchParams.get("include") !== "facts") return candidates(request);
    url.searchParams.delete("include");
    const candidateRequest = new Request(url.href, { method: request.method, signal: request.signal });
    const base = await candidates(candidateRequest), candidateLookup = await base.json();
    if (base.status !== 200) return respond(factsEnvelope(candidateLookup, "index-unavailable"), base);
    if (candidateLookup.candidateTotal === 0) return respond(factsEnvelope(candidateLookup, "source-key-not-found"), base);
    if (candidateLookup.candidateTotal > 1) return respond(factsEnvelope(candidateLookup, "selection-required"), base);
    try {
      need4(candidateLookup.candidateTotal === 1 && candidateLookup.candidates.length === 1);
      const originalFacts = await hydrateOriginal(candidateLookup, request, fetchImpl);
      return respond(factsEnvelope(candidateLookup, "verified-original-public-packet", originalFacts), base);
    } catch {
      return respond(factsEnvelope(candidateLookup, "facts-unavailable"), base, 503);
    }
  };
}
export {
  FACTS_BOUNDS,
  INDEX_RELEASE,
  ORIGIN,
  PREFIX,
  PUBLIC_BASE,
  RESOURCE_BOUNDS,
  createSourceBarcodeHandler2 as createSourceBarcodeHandler,
  keySha,
  selectOriginalPacket
};

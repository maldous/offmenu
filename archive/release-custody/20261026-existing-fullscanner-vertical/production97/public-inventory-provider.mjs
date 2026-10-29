// ../offmenu-worktrees/worker00-third-party-source-group-20261026/corpus/assert-curated.mjs
var forbidden = /* @__PURE__ */ new Set(["rawFields", "rawNutriments", "ingredientsText", "originalTextLines", "sealed", "credentials", "owner", "proofId"]);
function assertCurated(record) {
  if (!record?.id?.startsWith("offmenu:") || record.provenance?.visibility !== "public" || record.curation?.schema !== "offmenu-curation/1" || record.curation.rawSourcePayloadPublished !== false) throw Error("Not an OffMenu curation record");
  function scan(value) {
    if (!value || typeof value !== "object") return;
    for (const [key, item] of Object.entries(value)) {
      if (forbidden.has(key)) throw Error("Source/private payload cannot be published: " + key);
      scan(item);
    }
  }
  scan(record);
  return record;
}

// ../offmenu-worktrees/worker00-third-party-source-group-20261026/corpus/engine.mjs
var encoder = new TextEncoder();
var decoder = new TextDecoder();
var hash = async (value) => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", typeof value === "string" ? encoder.encode(value) : value)), (b) => b.toString(16).padStart(2, "0")).join("");
async function decompress(bytes) {
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip")), reader = stream.getReader();
  let total = 0, text = "";
  const decode = new TextDecoder();
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > 80 * 1024 * 1024) throw Error("Curated partition exceeds limit");
      text += decode.decode(value, { stream: true });
    }
    return text + decode.decode();
  } finally {
    await reader.cancel();
  }
}
var norm = (value) => value.normalize("NFKD").replace(/\p{M}/gu, "").toLowerCase();
function lineKey(line) {
  const match = /^\s*\[\s*("(?:\\.|[^"\\])*")\s*,/.exec(line);
  if (!match) throw Error("Invalid curation partition line");
  return JSON.parse(match[1]);
}
var CuratedQueryValidationError = class extends Error {
  constructor(message) {
    super(message);
    this.status = 400;
  }
};
async function createEngine(readBlob, { maxBlobReads = Infinity, maxPageEntries = 100 } = {}) {
  const bytes = await readBlob("manifest.json");
  if (!bytes) throw Error("Curated release is not published");
  const manifest = JSON.parse(decoder.decode(bytes));
  if (manifest.format !== "offmenu-curated/1" || manifest.status !== "curated-release-ready" || manifest.privateProviderData !== false || manifest.acquisitionAtRuntime !== false) throw Error("Unaccepted curation manifest");
  const files2 = new Map(manifest.files.map((f) => [f.key, f]));
  async function load(key) {
    const metadata = files2.get(key);
    if (!metadata) return null;
    const data = await readBlob(key);
    if (!data) throw Error("Curated release file missing");
    const compressed = new Uint8Array(data);
    if (compressed.byteLength !== metadata.bytes || await hash(compressed) !== metadata.sha256) throw Error("Curated release checksum failed");
    return decompress(compressed);
  }
  async function posting(namespace, key, source, read) {
    const text = await read(`${namespace}/${(await hash(key)).slice(0, manifest.shardLength)}.jsonl.gz`);
    if (!text) return [];
    for (const line of text.split("\n")) {
      if (!line) continue;
      if (lineKey(line) === key) return JSON.parse(line)[1][source] || [];
    }
    return [];
  }
  async function lookup({ source, query = "", barcode = "", kind = "", country = "", cursor = "", limit = 20 } = {}) {
    let reads = 0;
    const read = async (key) => {
      if (reads >= maxBlobReads) throw Error("Search needs too many index reads; use fewer search terms.");
      reads++;
      return load(key);
    };
    const definition = manifest.sources[source];
    if (!definition) throw Error("Source absent from curated release");
    if (typeof query !== "string" || query.length > 100 || barcode && !/^\d{4,32}$/.test(barcode) || country && !/^[A-Z]{2}$/.test(country) || kind && !/^[A-Za-z]+$/.test(kind) || cursor.length > 600) throw new CuratedQueryValidationError("Invalid collection filter");
    const size = Math.max(1, Math.min(100, maxPageEntries, Number(limit) || 20));
    const filters = await hash(JSON.stringify([source, query, barcode, kind, country]));
    let offset = 0;
    if (cursor) {
      let decoded;
      try {
        decoded = JSON.parse(atob(cursor.replaceAll("-", "+").replaceAll("_", "/")));
      } catch {
        throw new CuratedQueryValidationError("Invalid cursor");
      }
      if (!decoded || typeof decoded !== "object" || Array.isArray(decoded)) throw new CuratedQueryValidationError("Invalid cursor");
      if (decoded.release !== manifest.manifestSha256 || decoded.filters !== filters) throw new CuratedQueryValidationError("Cursor belongs to a different release or search");
      if (!Number.isSafeInteger(decoded.offset) || decoded.offset < 0) throw new CuratedQueryValidationError("Invalid cursor");
      offset = decoded.offset;
    }
    let candidates = null;
    if (barcode) candidates = await posting("barcodes", barcode, source, read);
    const unicodeTerms = [...new Set(norm(query).match(/[\p{L}\p{N}]+/gu) || [])];
    for (const term of unicodeTerms) {
      const found = await posting("terms", term, source, read);
      if (candidates === null) candidates = found;
      else {
        const set = new Set(found);
        candidates = candidates.filter((id) => set.has(id));
      }
      if (!candidates.length) break;
    }
    if (country && definition.countryIndex) {
      const text = await read(`countries/${source}/${country}-${kind || "all"}.json.gz`), found = text ? JSON.parse(text) : [];
      if (candidates === null) candidates = found;
      else {
        const intersection = [];
        let i = 0, j = 0;
        while (i < candidates.length && j < found.length) {
          if (candidates[i] === found[j]) {
            intersection.push(candidates[i]);
            i++;
            j++;
          } else if (candidates[i] < found[j]) i++;
          else j++;
        }
        candidates = intersection;
      }
    }
    const [start, end] = definition.entryRange, total = candidates?.length ?? end - start;
    if (offset > total) throw new CuratedQueryValidationError("Cursor outside collection");
    const pages = /* @__PURE__ */ new Map(), selected = [], recordShards = /* @__PURE__ */ new Set();
    let examined = 0;
    while (offset < total && selected.length < size && examined < 1e4) {
      const id = candidates ? candidates[offset] : start + offset;
      const pageId = Math.floor(id / manifest.entryPageSize);
      if (!pages.has(pageId)) {
        if (reads + 1 + recordShards.size > maxBlobReads) break;
        const text = await read(`entries-${pageId}.json.gz`);
        if (!text) throw Error("Entry index missing");
        pages.set(pageId, JSON.parse(text));
      }
      const entry = pages.get(pageId).find((e) => e.id === id);
      if (!entry || entry.source !== source) throw Error("Entry index mismatch");
      if (kind && !entry.kinds.includes(kind) || country && !entry.countries.includes(country)) {
        offset++;
        examined++;
        continue;
      }
      if (reads + recordShards.size + (recordShards.has(entry.shard) ? 0 : 1) > maxBlobReads) break;
      recordShards.add(entry.shard);
      offset++;
      examined++;
      selected.push(entry);
    }
    if (!examined && offset < total) throw Error("Search needs too many index reads; use fewer search terms.");
    const buckets = /* @__PURE__ */ new Map();
    for (const e of selected) {
      if (!buckets.has(e.shard)) buckets.set(e.shard, /* @__PURE__ */ new Map());
      buckets.get(e.shard).set(e.key, e);
    }
    const recordsByKey = /* @__PURE__ */ new Map(), pending = [...buckets];
    let nextBucket = 0;
    await Promise.all(Array.from({ length: Math.min(4, pending.length) }, async () => {
      while (nextBucket < pending.length) {
        const [shard, keys] = pending[nextBucket++], text = await read(`records/${source}/${shard}.jsonl.gz`);
        if (!text) throw Error("Record partition missing");
        for (const line of text.split("\n")) {
          if (!line) continue;
          const key = lineKey(line);
          if (keys.has(key)) recordsByKey.set(key, JSON.parse(line)[1].map(assertCurated));
        }
      }
    }));
    const records = selected.flatMap((e) => {
      const rows = recordsByKey.get(e.key);
      if (!rows) throw Error("Record missing from curation partition");
      return rows.filter((r) => !kind || r.kind === kind);
    });
    if (encoder.encode(JSON.stringify(records)).byteLength > 4 * 1024 * 1024) throw Error("Reduce page size: response exceeds limit");
    return {
      schemaVersion: "1.0",
      source,
      records,
      releaseId: manifest.releaseId,
      nextCursor: offset < total ? btoa(JSON.stringify({ release: manifest.manifestSha256, filters, offset })).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "") : null,
      coverage: { curatedRecords: definition.records, normalizedLocalRecords: definition.normalizedLocalRecords, rawSourcePayloadPublished: false, independentAcceptance: false },
      sourceTerms: definition.license
    };
  }
  return { manifest, lookup };
}

// ../offmenu-data/runtime/layout-migration/worker19/public-inventory-binding-and-samples-20261026/candidate/cloud/qualified-public-inventory.mjs
var PUBLIC_ORIGIN = "https://offmenu-corpus.netlify.app";
var sha = (value) => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
var digest = async (bytes) => [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map((x) => x.toString(16).padStart(2, "0")).join("");
var safe = (value) => typeof value === "string" && value.split("/").every((part) => /^[-A-Za-z0-9._]+$/.test(part) && part !== "." && part !== "..");
var headers = { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" };
var reply = (data, status) => Response.json(data, { status, headers });
async function createQualifiedPublicInventory({ selection, servedOrigin, fetchPublicFile } = {}) {
  if (!selection || !safe(selection.releaseId) || selection.releaseId.includes("/") || !sha(selection.manifestSha256) || typeof selection.sourceId !== "string" || !/^[-a-z0-9]+$/.test(selection.sourceId) || typeof fetchPublicFile !== "function")
    throw Error("EXISTING_QUALIFIED_PUBLIC_SELECTION_AND_FILE_PROVIDER_REQUIRED");
  const target = new URL(servedOrigin);
  if (target.origin !== servedOrigin || !["http:", "https:"].includes(target.protocol)) throw Error("EXACT_SERVED_ORIGIN_REQUIRED");
  const selected = Object.freeze({ ...selection }), base = PUBLIC_ORIGIN + "/products-selected/" + selected.releaseId;
  const manifestURL = new URL(selected.manifestURL ?? base + "/manifest.json");
  const fileBase = new URL(selected.fileBaseURL ?? base + "/releases/" + selected.releaseId + "/");
  for (const url of [manifestURL, fileBase]) if (url.origin !== PUBLIC_ORIGIN || url.username || url.password || url.search || url.hash || !safe(url.pathname.slice(1).replace(/\/$/, ""))) throw Error("EXISTING_PUBLIC_FILE_NAMESPACE_REQUIRED");
  if (!manifestURL.pathname.endsWith("/manifest.json") || !fileBase.pathname.endsWith("/"))
    throw Error("EXACT_PUBLIC_MANIFEST_AND_FILE_BASE_REQUIRED");
  async function bytesAt(url) {
    const response = await fetchPublicFile(url, { method: "GET", redirect: "error", credentials: "omit", cache: "no-store" });
    if (!response?.ok) throw Error("QUALIFIED_PUBLIC_FILE_UNAVAILABLE");
    const bytes = new Uint8Array(await response.arrayBuffer());
    if (bytes.byteLength > 10 * 1024 * 1024) throw Error("QUALIFIED_PUBLIC_FILE_BOUND");
    return bytes;
  }
  const manifestBytes = await bytesAt(manifestURL.href);
  if (await digest(manifestBytes) !== selected.manifestSha256) throw Error("PUBLIC_MANIFEST_BYTE_PIN_CHANGED");
  const manifest = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(manifestBytes));
  if (manifest.releaseId !== selected.releaseId || manifest.format !== "offmenu-curated/1" || manifest.status !== "curated-release-ready" || manifest.privateProviderData !== false || manifest.acquisitionAtRuntime !== false || manifest.curatedAcceptance?.status !== "all-curated-records-exercised" || !manifest.sources?.[selected.sourceId] || !Array.isArray(manifest.files)) throw Error("EXISTING_PUBLIC_RELEASE_CONTRACT_REQUIRED");
  const files2 = new Map(manifest.files.map((file) => [file.key, file]));
  const engine = await createEngine(async (key) => {
    if (key === "manifest.json") return new Uint8Array(manifestBytes);
    if (!safe(key) || !files2.has(key)) throw Error("UNLISTED_PUBLIC_FILE");
    return bytesAt(new URL(key, fileBase).href);
  }, { maxBlobReads: 24, maxPageEntries: 25 });
  return Object.freeze({
    describe() {
      const source = manifest.sources[selected.sourceId];
      return structuredClone({
        selection: { ...selected },
        servedOrigin,
        manifestURL: manifestURL.href,
        fileBaseURL: fileBase.href,
        records: source.records,
        normalizedLocalRecords: source.normalizedLocalRecords,
        withheldRecords: source.withheldRecords ?? null,
        independentAcceptance: typeof source.independentlyAccepted === "boolean" ? source.independentlyAccepted : null,
        scope: source.scope,
        acquisitionAtRuntime: false,
        privateProviderData: false
      });
    },
    async handle(request) {
      const url = new URL(request.url);
      if (url.pathname !== "/api/data/public") return null;
      if (url.origin !== servedOrigin) return reply({ error: "EXACT_PUBLIC_INVENTORY_ORIGIN_REQUIRED" }, 403);
      if (request.method !== "GET") return reply({ error: "METHOD_NOT_ALLOWED" }, 405);
      const names = [...url.searchParams.keys()], allowed = ["source", "releaseId", "manifestSha256", "barcode", "kind", "cursor", "limit"];
      if (new Set(names).size !== names.length || names.some((name) => !allowed.includes(name)) || url.searchParams.get("source") !== selected.sourceId || url.searchParams.get("releaseId") !== selected.releaseId || url.searchParams.get("manifestSha256") !== selected.manifestSha256)
        return reply({ error: "EXACT_PUBLIC_INVENTORY_SELECTION_REQUIRED" }, 409);
      const barcode = url.searchParams.get("barcode"), kind = url.searchParams.get("kind") ?? "product";
      const limit = url.searchParams.get("limit") ?? "25";
      if (!/^\d{4,32}$/.test(barcode || "") || kind !== "product" || !/^([1-9]|1\d|2[0-5])$/.test(limit))
        return reply({ error: "EXACT_PUBLIC_PRODUCT_QUERY_REQUIRED" }, 400);
      try {
        const value = await engine.lookup({
          source: selected.sourceId,
          barcode,
          kind,
          cursor: url.searchParams.get("cursor") ?? "",
          limit: Number(limit)
        });
        const output = { ...value, manifestSha256: selected.manifestSha256 };
        if (new TextEncoder().encode(JSON.stringify(output)).length > 262144) throw Error("PUBLIC_RESPONSE_BOUND");
        return reply(output, 200);
      } catch (error) {
        return reply({ error: error?.status === 400 ? "PUBLIC_QUERY_INVALID" : "PUBLIC_INVENTORY_UNAVAILABLE" }, error?.status === 400 ? 400 : 503);
      }
    }
  });
}
async function createQualifiedPublicInventorySet({ selections, servedOrigin, fetchPublicFile } = {}) {
  if (!Array.isArray(selections) || !selections.length) throw Error("EXISTING_QUALIFIED_PUBLIC_SELECTION_LIST_REQUIRED");
  selections = selections.map((selection) => Object.freeze({ ...selection }));
  const keys = /* @__PURE__ */ new Set();
  for (const selection of selections) {
    const key = JSON.stringify([selection.sourceId, selection.releaseId]);
    if (keys.has(key)) throw Error("AMBIGUOUS_PUBLIC_SOURCE_RELEASE_SELECTION");
    keys.add(key);
  }
  const inventories = [];
  for (const selection of selections) inventories.push(await createQualifiedPublicInventory({ selection, servedOrigin, fetchPublicFile }));
  return Object.freeze({
    describe: () => inventories.map((inventory) => inventory.describe()),
    async handle(request) {
      const url = new URL(request.url);
      if (url.pathname !== "/api/data/public") return null;
      const index = selections.findIndex((selection) => selection.sourceId === url.searchParams.get("source") && selection.releaseId === url.searchParams.get("releaseId"));
      return index < 0 ? null : inventories[index].handle(request);
    }
  });
}

// ../offmenu-data/runtime/layout-migration/worker00/selected-corpus-local-binding-20261026/six-public-file-fetch.mjs
var files = Object.freeze({ "https://offmenu-corpus.netlify.app/products-selected/offmenu-off-selected-products-20261025-v1/manifest.json": { "body": "eyJmb3JtYXQiOiJvZmZtZW51LWN1cmF0ZWQvMSIsInJlbGVhc2VJZCI6Im9mZm1lbnUtb2ZmLXNlbGVjdGVkLXByb2R1Y3RzLTIwMjYxMDI1LXYxIiwiZW5naW5lVmVyc2lvbiI6Im9mZm1lbnUtbG9jYWwtZW5naW5lLzEiLCJjdXJhdGlvblBvbGljeSI6eyJ2ZXJzaW9uIjoib2ZmbWVudS1jdXJhdGlvbi8xIiwibW9kZSI6Im1hbnVhbGx5LXRyaWdnZXJlZC1sb2NhbCIsInB1YmxpY1NvdXJjZXMiOlsib2ZmIiwicHJpY2VzIiwidXNkYS1maWxlcyIsIndpa2lib29rcyIsImFmY2QiLCJjaXF1YWwiLCJjb2ZpZCIsImdlcm1hbnktYmxzIiwibWF0dmFyZXRhYmVsbGVuIiwiZnJpZGEiLCJ3aWtpZGF0YS1mb29kLWJ1c2luZXNzZXMiLCJkaWV0YXJ5LWd1aWRlbGluZXMiLCJjbmYiLCJtZXh0Iiwib3ZlcnR1cmUtZm9vZC1wbGFjZXMiLCJmaW5lbGkiLCJmb29kZmlsZXMiLCJzd2VkZW4tZm9vZCIsIndvcmxkLXJlY2lwZXMiXSwicHJpdmF0ZUtpbmRzIjpbImhlYWx0aE9ic2VydmF0aW9uIiwiYWN0aXZpdHkiLCJpbnRha2VSZWNvcmQiLCJwYW50cnlMb3QiLCJtZWFsUGxhbiIsIndhc3RlUmVjb3JkIl0sInJ1bGVzIjp7InZpc2liaWxpdHkiOiJwdWJsaWMgb25seTsgbmV2ZXIgdXNlciBwcm92aWRlciByZXNwb25zZXMiLCJ1bmtub3duIjoicmV0YWluIG51bGxzIGFuZCBvcmlnaW5hbCBxdWFsaWZpZXJzIiwiaWRlbnRpdHkiOiJuYW1lc3BhY2VkIHN0cmluZ3M7IG5vIG5hbWUtb25seSBpZGVudGl0eSBtZXJnZSIsInF1YWxpZmljYXRpb24iOiJzb3VyY2UgYXNzZXJ0aW9ucyBhcmUgbm90IHZlcmlmaWVkIGRpZXRhcnkgc3VpdGFiaWxpdHkiLCJyZWNpcGVzIjoibWFudWFsIHJldmlldyByZXF1aXJlZCBiZWZvcmUgYXV0b21hdGljIHBsYW5uaW5nL2Nvb2tpbmciLCJjb21tZXJjaWFsIjoiQllPQywgYWNjb3VudCBhbmQgY29udHJhY3Qgc2NvcGU7IG5vIHB1YmxpYyBwcm9tb3Rpb24gYnkgZGVmYXVsdCIsIm93bmVyc2hpcE9yaWdpbiI6ImRhdGVkIGV2aWRlbmNlIHJlcXVpcmVkOyBiYXJjb2RlIHByZWZpeCBkb2VzIG5vdCBwcm92ZSBvcmlnaW4iLCJwdWJsaWNhdGlvbiI6ImltbXV0YWJsZSBpbmRleGVkIHJlbGVhc2U7IGFsbCBzb3VyY2VzIHJlY29uY2lsZWQgYmVmb3JlIG1hbmlmZXN0IGFjdGl2YXRpb24ifX0sImVudHJ5UGFnZVNpemUiOjEwMDAsInNoYXJkTGVuZ3RoIjozLCJzb3VyY2VzIjp7Im9mZiI6eyJzb3VyY2VJZCI6Im9mZiIsInJlbGVhc2VJZCI6IjIwMjYtMTAtMTIiLCJyZWNvcmRzIjoxLCJub3JtYWxpemVkTG9jYWxSZWNvcmRzIjoyLCJ3aXRoaGVsZFJlY29yZHMiOjEsIndpdGhoZWxkUmVhc29ucyI6eyJ1c2FibGUgZm9vZCBpZGVudGl0eSB1bnJlc29sdmVkIjoxfSwiYnVuZGxlcyI6MSwicmVjb3JkU2hhcmRMZW5ndGgiOjEsImVudHJ5UmFuZ2UiOlswLDFdLCJzY29wZSI6IkV4YWN0bHkgdHdvIG93bmVyLXNlbGVjdGVkIGFscmVhZHktcXVhbGlmaWVkIHNhbml0aXplZCBPRkYgcHJvamVjdGVkIHNjYWxhciByZWNvcmRzOjQwNjE0NjQ5Mzk3Mzgga25vd24gbmFtZSBhbmQzMDE3NjIwNDIyMDAzIGlkZW50aWZpZXItb25seSB1bmtub3duLiBUaGlzIGlzIG5vdCBhIHNvdXJjZS13aWRlIG9yIGNvdW50cnktY29tcGxldGUgcmVsZWFzZS4iLCJsaWNlbnNlIjoiT0RiTCAvIERiQ0w7IGltYWdlcyBDQyBCWS1TQSIsImF0dHJpYnV0aW9uIjoiT3BlbiBGb29kIEZhY3RzIiwiYXJjaGl2ZVNoYTI1NiI6IjExZjUwNTE1ZGM3OTE4MWYzODVkZjhlNTlkMzdhZTVkZGI4NWI5YjkzMmY4NGI2NDExMDU1ZTAyNmQ4NDY4MGUiLCJyYXdTb3VyY2VQYXlsb2FkUHVibGlzaGVkIjpmYWxzZSwicmlnaHRzIjoiT3JpZ2luYWwgc291cmNlIGxpY2VuY2UvYXR0cmlidXRpb24gcmV0YWluZWQ7IG5vIHByaXZhdGUgcHJvdmlkZXIgcmVzdWx0cyIsImluZGVwZW5kZW50bHlBY2NlcHRlZCI6ZmFsc2V9fSwic3RhdHVzIjoiY3VyYXRlZC1yZWxlYXNlLXJlYWR5IiwicHJpdmF0ZVByb3ZpZGVyRGF0YSI6ZmFsc2UsImFjcXVpc2l0aW9uQXRSdW50aW1lIjpmYWxzZSwiZW50cmllcyI6MSwicmVjb3JkcyI6MSwiZW50cnlQYWdlcyI6MSwiZmlsZXMiOlt7ImtleSI6ImJhcmNvZGVzLzlmNi5qc29ubC5neiIsImJ5dGVzIjo2Niwic2hhMjU2IjoiNTU3ZTA4MTAxMDQ3YjAxNDMyODQ4ZTEwMGE0OGE0ZWU4NmQxZjlhZDE2ZDFkNDU4NGM0ZGNlOTQwM2IwNjZiMCJ9LHsia2V5IjoiZW50cmllcy0wLmpzb24uZ3oiLCJieXRlcyI6MTU4LCJzaGEyNTYiOiI5NmQ3ZDMzNDRjMWM1NDQyMzUwNGViYjBkODhjMzc2NDA1Y2NmYWM1NDJkMDRmNzgxOGRhZmY0ZmQxNTcxY2ViIn0seyJrZXkiOiJyZWNvcmRzL29mZi9lLmpzb25sLmd6IiwiYnl0ZXMiOjg5OCwic2hhMjU2IjoiNzZmMDQ2ZjRiNGFjNTFjOTk3MWQ3YzdlMGJhNmJiYzg4MjNmZDkwMGMzOTc1NzI5ODM3YWU1MzYyNDRmMWNhNyJ9LHsia2V5IjoidGVybXMvNWM2Lmpzb25sLmd6IiwiYnl0ZXMiOjYxLCJzaGEyNTYiOiIwYzA5NjJjODdmNmE2ODhlNjcwNmM0MmI5YTFlYTZiNzdmNWJhMzg5M2EyYzVlNzFmMDEzY2U1YTFlNGQ2ODE0In0seyJrZXkiOiJ0ZXJtcy9lOTguanNvbmwuZ3oiLCJieXRlcyI6NTksInNoYTI1NiI6ImNlNTcxNTMyYjExZTc2OTc2ZTkwYjcwZWY5YjVhNGEyOTU4MjU2Nzg5ZTY5ZjM0ODM2MzI5ZmNiMzhkMjhjMmYifV0sImNvbXBsZXRlZEF0IjoiMjAyNi0xMC0yNVQxMTo1NDowMy43NDAxODErMDA6MDAiLCJjdXJhdGVkQWNjZXB0YW5jZSI6eyJzdGF0dXMiOiJhbGwtY3VyYXRlZC1yZWNvcmRzLWV4ZXJjaXNlZCIsInJlbGVhc2VJZCI6Im9mZm1lbnUtb2ZmLXNlbGVjdGVkLXByb2R1Y3RzLTIwMjYxMDI1LXYxIiwicmVjb3JkcyI6MSwicmF3U291cmNlUGF5bG9hZFB1Ymxpc2hlZCI6ZmFsc2UsImluZGVwZW5kZW50bHlBY2NlcHRlZCI6ZmFsc2UsImh1bWFuUmV2aWV3ZWQiOmZhbHNlLCJtZXRob2QiOiJBdXRob3IgYm91bmRlZCBhY3R1YWwtb3V0cHV0IGNoZWNrc3VtL2Fzc2VydEN1cmF0ZWQgYW5kIGV4aXN0aW5nIGVuZ2luZSBrbm93bjQwNi91bmtub3duMzAxIGhhcHB5LXBhdGggZXhlcmNpc2UuIiwia25vd24iOnsiYmFyY29kZSI6IjQwNjE0NjQ5Mzk3MzgiLCJyZWNvcmRzIjoxLCJuYW1lIjoiU2xpY2VkIEJlZXRyb290IiwiYnJhbmQiOiJOZXcgU2Vhc29uIEZyb20gQWxkaSJ9LCJ1bmtub3duIjp7ImJhcmNvZGUiOiIzMDE3NjIwNDIyMDAzIiwicmVjb3JkcyI6MCwicmVhc29uIjoiU2VsZWN0ZWQgaWRlbnRpZmllci1vbmx5IG5hbWUgd2l0aGhlbGQgYnkgdW5jaGFuZ2VkIGV4aXN0aW5nIGN1cmF0aW9uIHBvbGljeTsgbm90IGdsb2JhbCBzb3VyY2UgYWJzZW5jZS4ifSwiaW1hZ2VBc3NvY2lhdGlvbnNJbmNsdWRlZCI6MCwiR29sZEFkbWl0dGVkIjowLCJjb21wbGV0ZWRBdCI6IjIwMjYtMTAtMjVUMTE6NTc6NDUuOTMyWiIsImxpbWl0YXRpb24iOiJPbmUgY3VyYXRlZCBwcm9kdWN0IGZyb20gdHdvIHNlbGVjdGVkIHNhbml0aXplZCBPRkYgc2NhbGFyIHJlY29yZHMuIE5vdCBmdWxsIGNvcnB1cy9jb3VudHJ5L2Zvb2QvaW5ncmVkaWVudC9zY2llbnRpZmljL0dvbGQgYWNjZXB0YW5jZTsgbm8gYWN0dWFsIG5ldHdvcmssIHByaXZhdGUgREIgb3IgcHJvZHVjdGlvbiBvcGVyYXRpb24uIn0sIm1hbmlmZXN0U2hhMjU2IjoiNjgwMjlkOTU2NjZmN2ZmNDdlMTZjNzNmY2MzNmYwYzk4OTFhMGIxNjJkOTEyOWYxNzFkMjdmZTgxN2Q2ZGFjYSJ9Cg==", "sha256": "1bf09a371a164ebd8215fd9b44a1b2ac9816caaa65cd13504086defad76d4e8f", "bytes": 3697, "type": "application/json" }, "https://offmenu-corpus.netlify.app/products-selected/offmenu-off-selected-products-20261025-v1/releases/offmenu-off-selected-products-20261025-v1/barcodes/9f6.jsonl.gz": { "body": "H4sICNvt3WoE/zlmNi5qc29ubACKVjIxMDM0MTOxNLY0N7ZQ0qlWyk9LU7KKNoitjeUCAAAA//8DAFRRKuceAAAA", "sha256": "557e08101047b01432848e100a48a4ee86d1f9ad16d1d4584c4dce9403b066b0", "bytes": 66, "type": "application/gzip" }, "https://offmenu-corpus.netlify.app/products-selected/offmenu-off-selected-products-20261025-v1/releases/offmenu-off-selected-products-20261025-v1/entries-0.json.gz": { "body": "H4sICNvt3WoC/2VudHJpZXMtMC5qc29uACyNywqDMBREf6XMOgsbEWt+RVzkcUNDa27JYyGl/26C3c0ZODPrF8FBDQKZa7IEBfYeAi86rrxTrOqT2FVb1Dh4I+9GP+QiydMizTyN0+yakJ86tSVQl0N0GWrF38MmYLnGkgL1vmHUez/L72DJ3QxRScwFv+0EAAD//wMAhWAff5IAAAA=", "sha256": "96d7d3344c1c54423504ebb0d88c376405ccfac542d04f7818daff4fd1571ceb", "bytes": 158, "type": "application/gzip" }, "https://offmenu-corpus.netlify.app/products-selected/offmenu-off-selected-products-20261025-v1/releases/offmenu-off-selected-products-20261025-v1/records/off/e.jsonl.gz": { "body": "H4sICNvt3WoE/2UuanNvbmwAjFTLbiM3ELznK4g56zV6Sz7t2jCwgLO7sYAEC8MHPnokxhxywocUZeF/T3FmJHuDPeSkEdms7q7q6qfCVVVNNm0b71SScTubVGJaCr6ebqZU0WYqVovZYqWKwdP3IsgD1fx38kE7W2yLcjQpBoVW+Pz/OMWLtvlFnxEA0iUbvaZQbJ+eB/niSJZbScUWOV3ykj71ORDtSTqv2oP5ZFnOl/PNbLOarXGVvAHwIcYmbMfjk/NGjVxDtnJOVVzGMHJ+jzijJdkA+OLLnXhgY3Ynbh9umK75ngK7vWUfvw13HxDII+oSKXbtfgEUuwcWu89gbS2GeOiqm06my2E5GZbTNkOtI8/vdvghUBxzNmvOLJAhGUmxwK2O+h98eYpcW3yg9T9xiWcsSG64DyO2awlgysmUYdiBhwPTCp+6AmfvYOiYjyUNmHWROa/32nLDmiSMDgfyTJwjAfEzr2ksPLeKcU8sNSF64vW77OHm+nyIJAbF5jZYfmK43ScQNWANly8soIMBywyPtd17UjoXKQ0PAfXJloP2Xcsu40euDRfa6Hjustu/Eje5FYXK3EUE55nnJ/YGObYpzwiwG342jivcSZMUnmUh9P4ARUDxpetubpjikbPutq3inaJX2kfsU6v8WLo8h9Ab2du2A6O/+yTswUERJkGBBiiBLWq47/pzEPamI7rvWEOY7p6geUO+cr6GwuLM/nD+hfxkkuvuqrzrtd0d+HSxRBcrsa4qGJCL9XyxmM/XREKJal4tJeZ9NS/FRk35RgipKiqVWopyKSdqoXipZrReAvmog+5oBl47AhKnEaqHXAoOe8sOZeq6GJfFK8zY/2u91/r956HwqYOPzm/b4Cd4lwYfW88+YqH4PKAd4nXn/NfGedZSFvNilWFH07D1MLo4pJrbR4w7nQiLoeImEMwK3WroIe80xd+6oerUuIZgpDo7fe1m6GtvjQsI+s8Dk3u3MAlK2OVdodhHouidi0ieL1Dcd8S2HkLQZzqxHRYBbHvvXc0+GKURmf2RoRJ8XmxtMgaycJOAm/8A4Gpjn3cflt05YFkAUXAvnSKA9A+KH0l6fUYh2RB5V+Rd2KG/2eXWgecmWyKv1LfzX3nT4F/eSi3FyXoKzhzB46DondiR9i7kxbqTLV5fn59/+RcAAP//AwDnoTYuMgYAAA==", "sha256": "76f046f4b4ac51c9971d7c7e0ba6bbc8823fd900c3975729837ae536244f1ca7", "bytes": 898, "type": "application/gzip" }, "https://offmenu-corpus.netlify.app/products-selected/offmenu-off-selected-products-20261025-v1/releases/offmenu-off-selected-products-20261025-v1/terms/5c6.jsonl.gz": { "body": "H4sICNvt3WoE/zVjNi5qc29ubACKVkpKTS0pys8vUdKpVspPS1OyijaIrY3lAgAAAP//AwB4HSu/GQAAAA==", "sha256": "0c0962c87f6a688e6706c42b9a1ea6b77f5ba3893a2c5e71f013ce5a1e4d6814", "bytes": 61, "type": "application/gzip" }, "https://offmenu-corpus.netlify.app/products-selected/offmenu-off-selected-products-20261025-v1/releases/offmenu-off-selected-products-20261025-v1/terms/e98.jsonl.gz": { "body": "H4sICNvt3WoE/2U5OC5qc29ubACKVirOyUxOTVHSqVbKT0tTsoo2iK2N5QIAAAD//wMAQvA8fxcAAAA=", "sha256": "ce571532b11e76976e90b70ef9b5a4a2958256789e69f34836329fcb38d28c2f", "bytes": 59, "type": "application/gzip" } });
async function selectedFetch(input, init = {}) {
  const url = new URL(typeof input === "string" ? input : input.url || String(input));
  const method = init.method || (input instanceof Request ? input.method : "GET");
  if (method !== "GET" || url.username || url.password || url.search || url.hash || !Object.hasOwn(files, url.href)) throw Error("Local selected curation request is outside its six-file binding.");
  const f = files[url.href];
  return new Response(Uint8Array.from(atob(f.body), (c) => c.charCodeAt(0)), { headers: { "Content-Type": f.type, "Cache-Control": "no-store", "X-OffMenu-Local-Public-File-SHA256": f.sha256 } });
}

// ../offmenu-data/runtime/layout-migration/worker19/public-inventory-binding-and-samples-20261026/candidate/cloud/existing-public-inventory-bootstrap.mjs
var EXISTING_PUBLIC_INVENTORY_SELECTION = Object.freeze({
  sourceId: "off",
  releaseId: "offmenu-off-selected-products-20261025-v1",
  manifestSha256: "1bf09a371a164ebd8215fd9b44a1b2ac9816caaa65cd13504086defad76d4e8f",
  manifestURL: "https://offmenu-corpus.netlify.app/products-selected/offmenu-off-selected-products-20261025-v1/manifest.json",
  fileBaseURL: "https://offmenu-corpus.netlify.app/products-selected/offmenu-off-selected-products-20261025-v1/releases/offmenu-off-selected-products-20261025-v1/"
});
function bindExistingQualifiedPublicInventory(servedOrigin) {
  return createQualifiedPublicInventorySet({
    servedOrigin,
    selections: [EXISTING_PUBLIC_INVENTORY_SELECTION],
    fetchPublicFile: selectedFetch
  });
}
export {
  EXISTING_PUBLIC_INVENTORY_SELECTION,
  bindExistingQualifiedPublicInventory
};

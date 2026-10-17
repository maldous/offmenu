// Deliberately unusable until the live authentication and snapshot schemas are verified.
// Do not replace this with heuristics for token fields, paused state, or message authorship.
export default {
  schemaVersion: 1,
  verified: false,
  extractCredential() { throw new Error('LOCAL_ADAPTER_UNVERIFIED'); },
  normalizeSnapshot() { throw new Error('LOCAL_ADAPTER_UNVERIFIED'); }
};

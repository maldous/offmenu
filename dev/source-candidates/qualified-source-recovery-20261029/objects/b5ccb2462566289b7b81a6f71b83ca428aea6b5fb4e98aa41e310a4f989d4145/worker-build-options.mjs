// Apply only to the Cloudflare Worker bundle, never browser entry points.
export const workerRuntimeBuildOptions = Object.freeze({
  conditions: Object.freeze(['workerd']),
  external: Object.freeze(['node:*']),
});

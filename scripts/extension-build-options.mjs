// Keep the application build and the read-only generated-file check identical.
export const extensionBuildOptions = Object.freeze({
  entryPoints: Object.freeze(['extension/popup-source.js']),
  bundle: true,
  minify: true,
  outfile: 'extension/popup.js',
});

import { build } from '/home/user/src/offmenu-data/dev-preview-20261014/workers/worker-05/live-dev/3a50a8b5-5f92-4394-a0e7-ef3a3f7c1879/production-app/node_modules/esbuild/lib/main.js';
import path from 'node:path';

const live = '/home/user/src/offmenu-data/dev-preview-20261014/workers/worker-05/live-dev/3a50a8b5-5f92-4394-a0e7-ef3a3f7c1879/production-app';
const candidate = path.resolve('indexed-product-client-handoff-v2/candidate/public');
await build({
  entryPoints: [path.join(candidate, 'shelf-scanner.js')],
  bundle: true,
  minify: true,
  format: 'esm',
  outfile: path.resolve('indexed-product-client-handoff-v2/candidate/offline-scanner-full-bundle.mjs'),
  plugins: [{
    name: 'live-unchanged-imports',
    setup(bundle) {
      bundle.onResolve({ filter: /^\.\// }, args => {
        if (args.importer.startsWith(candidate) && args.path !== './scanner-identifiers.js') {
          return { path: path.join(live, 'public', args.path.slice(2)) };
        }
      });
    },
  }],
});
console.log('Off-live scanner bundle built with unchanged live companion modules.');

// Runs the installed authenticated CLI with JSON data from a file.
// Avoids OS argv limits; never reads or prints credential values.
import {readFile} from 'node:fs/promises';
const [method,dataFile]=process.argv.slice(2);const data=await readFile(dataFile,'utf8');JSON.parse(data);
process.argv.splice(0,process.argv.length,process.execPath,'/usr/local/lib/node_modules/netlify-cli/bin/run.js','api',method,'--data',data);
await import('/usr/local/lib/node_modules/netlify-cli/bin/run.js');

import fs from 'node:fs';
import crypto from 'node:crypto';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);
const esbuild = require('/home/user/src/offmenu/node_modules/esbuild');
if (esbuild.version !== '0.25.12') throw Error('esbuild pin');
const base = new URL('./baseline/', import.meta.url), out = new URL('./candidate/', import.meta.url);
const sdk = fs.readFileSync(new URL('auth.js', base), 'utf8');
if (crypto.createHash('sha256').update(sdk).digest('hex') !== '61ab5315ca62cecba443e7fad2563fb4955e27930f7658b4b9a6fab8ac03f472') throw Error('preimage');
const a = sdk.indexOf('function ye('), b = sdk.indexOf('function we(', a);
if (a !== 26167 || b !== 29358) throw Error('controller boundary');
const controller = fs.readFileSync(new URL('./source/auth-controller.mjs', import.meta.url),'utf8')
 .replaceAll('export function ', 'function ').replaceAll('createAuthPageController', 'ye')
 .replaceAll('readAuthCallbackFlags', 'offmenuReadAuthCallbackFlags');
const image = fs.readFileSync(new URL('./source/google-sign-in-official.png',import.meta.url)).toString('base64');
const oldLabel='a.textContent="Sign in with "+c[o],a.onclick';
const newLabel='o==="google"?(a.className="google-sign-in",a.setAttribute("aria-label","Sign in with Google"),a.innerHTML='+JSON.stringify('<img width="177" height="40" alt="Sign in with Google" src="data:image/png;base64,'+image+'">')+'):a.textContent="Sign in with "+c[o],a.onclick';
let result = sdk.slice(0,a) + controller + sdk.slice(b);
if (result.split(oldLabel).length !== 2) throw Error('label boundary');
result=result.replace(oldLabel,newLabel);
esbuild.transformSync(result,{loader:'js',format:'esm',target:'es2022'}); // syntax only; leave SDK byte exact
fs.writeFileSync(new URL('auth.js',out), result);
let html=fs.readFileSync(new URL('auth.html',base),'utf8');
html=html.replace('</head>','<style>\n#auth-providers button.google-sign-in{all:unset;display:inline-flex;cursor:pointer;vertical-align:middle;border-radius:4px;margin:8px 0;max-width:100%}\n#auth-providers button.google-sign-in img{display:block;width:177px;height:40px;max-width:100%;object-fit:contain}\n#auth-providers button.google-sign-in:focus-visible{outline:3px solid #4285f4;outline-offset:3px}\n#auth-providers button.google-sign-in:hover{opacity:.92}\n</style></head>');
fs.writeFileSync(new URL('auth.html',out),html);
const bridge=fs.readFileSync(new URL('./source/auth-return-bridge.mjs',import.meta.url),'utf8');
fs.writeFileSync(new URL('auth-return-bridge.js',out),bridge);
console.log(JSON.stringify({esbuild:esbuild.version,sdkPrefixBytesPreserved:a,controllerReplaced:true,providerCallAndScopesUnchanged:true}));

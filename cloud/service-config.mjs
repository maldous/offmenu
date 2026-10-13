// Public service metadata is explicitly projected; secrets never enter this model.
import {serviceEmailConfigured} from './service-support.mjs';
const object = (value, name) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid '+name+'.');
  return value;
};
function keys(value, allowed, name) {
  object(value, name);
  if (Object.keys(value).some(key => !allowed.includes(key))) throw Error('Unknown '+name+' setting.');
}
const bool = (value, name) => {
  if (value === undefined) return false;
  if (typeof value !== 'boolean') throw Error('Invalid '+name+'.');
  return value;
};
const identifier = (value, name, pattern = /^[1-9]\d{0,14}$/) => {
  if (value === undefined || value === '') return '';
  if (typeof value !== 'string' || !pattern.test(value)) throw Error('Invalid '+name+'.');
  return value;
};
export function serviceLink(value, name = 'service link', hosts) {
  if (value === undefined || value === '') return '';
  if (typeof value !== 'string' || value.length > 500 || /[\s<>"'\\]/.test(value)) throw Error('Invalid '+name+'.');
  if (!hosts && /^\/(?!\/)/.test(value) && !value.includes('..') && !/%2e|%2f|%5c/i.test(value)) return value;
  let url;
  try { url = new URL(value); } catch { throw Error('Invalid '+name+'.'); }
  if (url.protocol !== 'https:' || url.username || url.password || url.port ||
      (hosts && !hosts.some(host => url.hostname === host || url.hostname.endsWith('.'+host)))) throw Error('Invalid '+name+'.');
  return url.href;
}
export function parseServiceConfig(raw) {
  if (raw === undefined || raw === '') raw = {};
  if (typeof raw === 'string') {
    if (raw.length > 12000) throw Error('Service configuration is too large.');
    try { raw = JSON.parse(raw); } catch { throw Error('Invalid service configuration JSON.'); }
  }
  keys(raw, ['client','links','seo'], 'service configuration');
  const client = raw.client || {}, links = raw.links || {}, seo = raw.seo || {};
  keys(client, ['diagnostics','analytics','consent','feedback','ads'], 'client');
  const diagnostics = client.diagnostics || {}, analytics = client.analytics || {}, consent = client.consent || {}, feedback = client.feedback || {}, ads = client.ads || {};
  keys(diagnostics, ['enabled'], 'diagnostics');
  keys(analytics, ['enabled','provider','purposeId'], 'analytics');
  keys(consent, ['siteId','cookiePolicyId','tcfEnabled','policyLanguage'], 'consent');
  keys(feedback, ['productId','boardUrl'], 'feedback');
  keys(ads, ['client','slot','approved'], 'ads');
  keys(links, ['status','privacy','source'], 'links');
  keys(seo, ['googleSiteVerification','bingSiteVerification'], 'seo');
  if (analytics.provider !== undefined && analytics.provider !== 'zaraz') throw Error('Unsupported analytics provider.');
  if (consent.policyLanguage !== undefined && !['en','en-GB','it','es','nl','fr','de','ru','pt','pt-BR','da'].includes(consent.policyLanguage)) throw Error('Unsupported privacy policy language.');
  const result = {
    client: {
      diagnostics: {enabled:bool(diagnostics.enabled,'diagnostics enabled')},
      analytics: {enabled:bool(analytics.enabled,'analytics enabled'),provider:'zaraz',purposeId:identifier(analytics.purposeId,'analytics purpose ID',/^[A-Za-z0-9_-]{1,100}$/)},
      consent: {siteId:identifier(consent.siteId,'consent site ID'),cookiePolicyId:identifier(consent.cookiePolicyId,'cookie policy ID'),tcfEnabled:bool(consent.tcfEnabled,'TCF enabled'),policyLanguage:consent.policyLanguage||'en'},
      feedback: {productId:identifier(feedback.productId,'feedback product ID'),boardUrl:serviceLink(feedback.boardUrl,'feedback board',['sleekplan.app','sleekplan.com'])},
      ads: {client:identifier(ads.client,'advertising client',/^ca-pub-\d{16}$/),slot:identifier(ads.slot,'advertising slot'),approved:bool(ads.approved,'advertising approval')}
    },
    links:Object.fromEntries(['status','privacy','source'].map(key=>[key,serviceLink(links[key],key+' link')])),
    seo:Object.fromEntries(['googleSiteVerification','bingSiteVerification'].map(key=>[key,identifier(seo[key],key,/^[A-Za-z0-9_-]{1,200}$/)]))
  };
  if (!!result.client.consent.siteId !== !!result.client.consent.cookiePolicyId) throw Error('Consent requires both site and policy IDs.');
  if (result.client.analytics.enabled && !result.client.analytics.purposeId) throw Error('Analytics requires a configured Zaraz consent purpose.');
  if (result.client.ads.approved && (!result.client.ads.client || !result.client.ads.slot || !result.client.consent.siteId || !result.client.consent.tcfEnabled)) throw Error('Advertising requires an approved site, slot and configured TCF consent.');
  return result;
}
export function sentryDestination(dsn) {
  if (!dsn || typeof dsn !== 'string' || dsn.length > 500) return null;
  try {
    const url = new URL(dsn);
    if (url.protocol !== 'https:' || url.port || url.password || url.search || url.hash ||
        !/^[a-f0-9]{16,64}$/i.test(url.username) || !/^\/\d+$/.test(url.pathname) ||
        !/^o\d+\.ingest(?:\.(?:us|de))?\.sentry\.io$/.test(url.hostname)) return null;
    return {url:'https://'+url.hostname+'/api'+url.pathname+'/envelope/',key:url.username};
  } catch { return null; }
}
export function validEmail(value) {
  return typeof value === 'string' && value.length <= 254 && /^[^\s<>"@]+@[^\s<>"@]+\.[^\s<>"@]+$/.test(value);
}
export function serviceConfiguration(env = {}) {
  let config, invalid = false;
  try { config = parseServiceConfig(env.THIRD_PARTY_CONFIG); }
  catch { config = parseServiceConfig({}); invalid = true; }
  const {client,links,seo} = config;
  const diagnostics = client.diagnostics.enabled && !!sentryDestination(env.SENTRY_DSN);
  const email = !!env.DB && serviceEmailConfigured(env);
  // Downgrade requested features without their server prerequisites.
  client.diagnostics.enabled = diagnostics;
  const entry = (id,name,category,available,reason) => ({id,name,category,status:available?'configured':'setup_required',reason:available?'Available when you choose to use it.':reason});
  const services = [
    entry('cloudflare','Cloudflare','hosting',true,'Managed hosting is required.'),
    entry('netlify-identity','Netlify Identity','identity',true,'Account service is required.'),
    entry('sentry','Sentry','diagnostics',diagnostics,'An OffMenu error-monitoring project must be configured.'),
    entry('brevo','Brevo','email',email,'An OffMenu sender and email service must be configured.'),
    entry('support','Support email','support',email && validEmail(env.SUPPORT_EMAIL),'A support recipient and email service must be configured.'),
    entry('iubenda','iubenda','consent',!!client.consent.siteId,'An OffMenu cookie policy must be configured.'),
    entry('sleekplan','Sleekplan','feedback',!!(client.feedback.productId || client.feedback.boardUrl),'An OffMenu feedback board must be configured.'),
    entry('zaraz','Cloudflare Zaraz','analytics',client.analytics.enabled,'An analytics consent purpose must be configured.'),
    entry('adsense','Google AdSense','advertising',client.ads.approved,'OffMenu site approval and advertising consent are required.'),
    entry('uptimerobot','Availability status','operations',!!links.status,'An OffMenu status page must be configured.'),
    entry('google-search','Google Search Console','discovery',!!seo.googleSiteVerification,'OffMenu property verification must be configured.'),
    entry('bing-search','Bing Webmaster Tools','discovery',!!seo.bingSiteVerification,'OffMenu site verification must be configured.')
  ];
  return {schemaVersion:1,configurationValid:!invalid,client,links,seo,services};
}
export function serviceCSP(env = {}) {
  const {client} = serviceConfiguration(env);
  const script = ["'self'","'wasm-unsafe-eval'"], connect=["'self'",'https://offmenu-corpus.netlify.app'], frame=[], image=["'self'",'blob:'];
  if (client.consent.siteId) {
    script.push('https://cdn.iubenda.com','https://cs.iubenda.com');
    connect.push('https://*.iubenda.com'); frame.push('https://*.iubenda.com');
  }
  if (client.feedback.productId) {
    script.push('https://client.sleekplan.com'); connect.push('https://*.sleekplan.com','https://*.sleekplan.app'); frame.push('https://*.sleekplan.com','https://*.sleekplan.app'); image.push('https://*.sleekplan.com','https://*.sleekplan.app');
  }
  if (client.ads.approved) {
    script.push('https://pagead2.googlesyndication.com','https://*.googlesyndication.com');
    connect.push('https://*.googlesyndication.com','https://*.doubleclick.net'); frame.push('https://*.googlesyndication.com','https://*.doubleclick.net'); image.push('https://*.googlesyndication.com','https://*.doubleclick.net');
  }
  return `default-src 'self'; script-src ${script.join(' ')}; style-src 'self' 'unsafe-inline'; img-src ${image.join(' ')}; media-src 'self' blob:; connect-src ${connect.join(' ')}; worker-src 'self'; frame-src ${frame.length?frame.join(' '):"'none'"}; object-src 'none'; base-uri 'self'; frame-ancestors 'none'`;
}
export function serviceHTML(html, env = {}) {
  const config = serviceConfiguration(env);
  const tags = Object.entries(config.seo).filter(([,value])=>value).map(([key,value])=>`<meta name="${key==='googleSiteVerification'?'google-site-verification':'msvalidate.01'}" content="${value}">`).join('');
  return html.replace('</head>',tags+'</head>');
}
export function serviceRoutes(request, env, {reply}) {
  const url = new URL(request.url);
  if (url.pathname === '/api/services') {
    if (request.method !== 'GET') return reply({error:'Method not allowed'},405);
    return reply(serviceConfiguration(env));
  }
  if (url.pathname === '/api/services/privacy') {
    if (request.method !== 'GET') return reply({error:'Method not allowed'},405);
    return reply({schemaVersion:1,optionalDefaults:'off',consentStorage:'this browser',
      categories:{diagnostics:'Fixed runtime error codes only; no exception text, URLs, identifiers or pantry data.',analytics:'Allowlisted coarse actions only after local and vendor-purpose consent.',support:'Only the message and reply email you confirm are sent to the configured support provider.',email:'Only your confirmed document is sent to your verified account email address.',advertising:'Optional approved advertising requires local choice and a valid vendor consent decision.'},
      retention:{supportPayloadDays:30,deliveryIdentity:'Retained to prevent uncertain delivery from being replayed.'},
      links:serviceConfiguration(env).links});
  }
  if (url.pathname === '/robots.txt' && request.method === 'GET') return new Response('User-agent: *\nDisallow: /api/\nDisallow: /oauth/\nDisallow: /.netlify/\nDisallow: /data-workspace.html\nSitemap: '+url.origin+'/sitemap.xml\n',{headers:{'Content-Type':'text/plain;charset=utf-8','Cache-Control':'public,max-age=300'}});
  if (url.pathname === '/sitemap.xml' && request.method === 'GET') {
    const origin = url.origin.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
    return new Response(`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>${origin}/</loc></url></urlset>`,{headers:{'Content-Type':'application/xml;charset=utf-8','Cache-Control':'public,max-age=300'}});
  }
  return null;
}

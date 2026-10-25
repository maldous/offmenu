import {betterAuth} from 'better-auth';

export const OFFMENU_AUTH_BASE_PATH = '/api/auth';
export const OFFMENU_AUTH_COOKIE_PREFIX = 'offmenu-auth';

function configuration(env, options) {
  if (!env?.DB || typeof env.DB.prepare !== 'function' || typeof env.DB.batch !== 'function') {
    throw new TypeError('OffMenu authentication requires a native D1 binding.');
  }
  let url;
  try { url = new URL(env.BETTER_AUTH_URL); } catch {
    throw new TypeError('OffMenu authentication requires an explicit HTTPS origin.');
  }
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || url.pathname !== '/') {
    throw new TypeError('OffMenu authentication requires an explicit HTTPS origin.');
  }
  if (typeof env.BETTER_AUTH_SECRET !== 'string' || env.BETTER_AUTH_SECRET.length < 32) {
    throw new TypeError('OffMenu authentication requires a separately provisioned secret of at least 32 characters.');
  }
  const {expiresIn, updateAge} = options.sessionPolicy || {};
  if (!Number.isSafeInteger(expiresIn) || expiresIn <= 0 ||
      !Number.isSafeInteger(updateAge) || updateAge < 0 || updateAge >= expiresIn) {
    throw new TypeError('An explicit session expiry and renewal policy is required.');
  }
  const email = options.email;
  if (email !== undefined && (!email || typeof email !== 'object' || typeof email.enabled !== 'boolean')) {
    throw new TypeError('Email authentication requires an explicit enabled setting.');
  }
  if (email?.enabled && (typeof email.sendVerificationEmail !== 'function' ||
      typeof email.sendResetPassword !== 'function' || typeof email.allowSignUp !== 'boolean')) {
    throw new TypeError('Email authentication requires verification/reset delivery and an explicit signup policy.');
  }
  return {origin: url.origin, expiresIn, updateAge, email};
}

/**
 * Explicit factory: the caller mounts its handler; no schema writes, secret generation or providers.
 * Email stays disabled unless a caller explicitly supplies its delivery hooks.
 * Never pass browser input as env or options. Keep sessionPolicy deployment-owned.
 */
export function createOffMenuAuth(env, options = {}) {
  const {origin, expiresIn, updateAge, email} = configuration(env, options);
  const emailEnabled = email?.enabled === true;
  return betterAuth({
    appName: 'OffMenu',
    database: env.DB,
    baseURL: origin,
    basePath: OFFMENU_AUTH_BASE_PATH,
    secret: env.BETTER_AUTH_SECRET,
    trustedOrigins: [origin],
    user: {
      modelName: 'auth_user',
      additionalFields: {
        // Imported trusted roles only. API input and provider profiles cannot set it.
        appRoles: {type: 'string', required: false, defaultValue: '[]', input: false},
      },
      changeEmail: {enabled: false},
      deleteUser: {enabled: false},
    },
    session: {
      modelName: 'auth_session',
      expiresIn,
      updateAge,
      cookieCache: {enabled: false},
    },
    account: {
      modelName: 'auth_account',
      encryptOAuthTokens: true,
      accountLinking: {enabled: false},
    },
    verification: {modelName: 'auth_verification'},
    // Google registration/consent is deliberately not activated by this slice.
    socialProviders: {},
    emailAndPassword: {
      enabled: emailEnabled,
      disableSignUp: !emailEnabled || !email.allowSignUp,
      requireEmailVerification: true,
      revokeSessionsOnPasswordReset: true,
      ...(emailEnabled ? {sendResetPassword: email.sendResetPassword} : {}),
    },
    emailVerification: {
      sendOnSignUp: emailEnabled,
      autoSignInAfterVerification: false,
      ...(emailEnabled ? {sendVerificationEmail: email.sendVerificationEmail} : {}),
    },
    rateLimit: {enabled: true, storage: 'database', modelName: 'auth_rate_limit'},
    advanced: {
      cookiePrefix: OFFMENU_AUTH_COOKIE_PREFIX,
      useSecureCookies: true,
      defaultCookieAttributes: {httpOnly: true, secure: true, sameSite: 'lax', path: '/'},
      crossSubDomainCookies: {enabled: false},
      ipAddress: {ipAddressHeaders: ['cf-connecting-ip']},
    },
    telemetry: {enabled: false},
  });
}

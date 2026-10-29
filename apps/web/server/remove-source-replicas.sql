-- Authorized by Matt on 13 October 2026. Run only when D1 writes are available.
-- Preserve mixed private records and every account/auth/vault/application table.
DELETE FROM unified_records WHERE owner LIKE 'public:%';
DELETE FROM products;
DELETE FROM price_observations;
-- No DROP statements: the account DB and unified_records are shared with users.

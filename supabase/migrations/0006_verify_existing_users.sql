-- Backfill email_verified_at for users registered before verification was enforced
UPDATE users
SET email_verified_at = created_at
WHERE email_verified_at IS NULL;

UPDATE refresh_tokens
SET revoked_at = NOW()
WHERE jti = $1
  AND revoked_at IS NULL;

UPDATE password_reset_tokens
SET used_at = NOW()
WHERE id = $1
  AND used_at IS NULL;

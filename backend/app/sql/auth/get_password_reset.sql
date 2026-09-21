SELECT
    id,
    user_id,
    token_hash,
    expires_at,
    used_at,
    created_at
FROM password_reset_tokens
WHERE token_hash = $1
LIMIT 1;

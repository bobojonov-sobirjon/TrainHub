SELECT
    id,
    user_id,
    jti,
    audience,
    expires_at,
    revoked_at,
    created_at
FROM refresh_tokens
WHERE jti = $1
LIMIT 1;

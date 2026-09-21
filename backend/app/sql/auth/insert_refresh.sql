INSERT INTO refresh_tokens (user_id, jti, audience, expires_at)
VALUES ($1, $2, $3, $4);

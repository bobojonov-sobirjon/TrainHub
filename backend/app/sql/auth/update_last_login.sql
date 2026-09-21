UPDATE users
SET last_login_at = NOW(),
    updated_at = NOW()
WHERE id = $1;

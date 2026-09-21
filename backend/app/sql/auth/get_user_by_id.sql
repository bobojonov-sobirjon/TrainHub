SELECT
    u.id,
    u.public_id,
    u.email,
    u.phone,
    u.password_hash,
    u.first_name,
    u.last_name,
    u.avatar_url,
    u.gender,
    u.birth_date,
    u.height_cm,
    u.is_shadow,
    u.is_active,
    u.is_blocked,
    u.created_at,
    u.last_login_at,
    COALESCE(
        array_agg(ur.role) FILTER (WHERE ur.role IS NOT NULL),
        ARRAY[]::text[]
    ) AS roles
FROM users u
LEFT JOIN user_roles ur ON ur.user_id = u.id
WHERE u.id = $1
GROUP BY u.id
LIMIT 1;

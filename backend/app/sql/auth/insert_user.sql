INSERT INTO users (
    public_id,
    email,
    phone,
    password_hash,
    first_name,
    last_name,
    gender,
    birth_date
)
VALUES (
    'TH' || LPAD(nextval('user_public_id_seq')::text, 9, '0'),
    $1,
    $2,
    $3,
    $4,
    $5,
    $6,
    $7
)
RETURNING
    id,
    public_id,
    email,
    phone,
    first_name,
    last_name,
    gender,
    birth_date,
    created_at;

SELECT
    id,
    category,
    code,
    title_ru,
    sort_order
FROM dictionaries
WHERE is_active = TRUE
ORDER BY category ASC, sort_order ASC, id ASC;

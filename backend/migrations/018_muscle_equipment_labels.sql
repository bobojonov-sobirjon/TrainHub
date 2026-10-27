-- Codes used by seed/catalog exercises that were missing from dictionaries.
INSERT INTO dictionaries (category, code, title_ru, sort_order) VALUES
    ('muscle_group', 'full_body', 'Всё тело', 13),
    ('muscle_group', 'arms', 'Руки', 14),
    ('muscle_group', 'legs', 'Ноги', 15),
    ('muscle_group', 'traps', 'Трапеции', 16),
    ('muscle_group', 'abs', 'Пресс', 17),
    ('muscle_group', 'press', 'Пресс', 18),
    ('equipment', 'bodyweight', 'Свой вес', 9),
    ('equipment', 'barbell', 'Штанга', 10),
    ('equipment', 'dumbbell', 'Гантель', 11),
    ('equipment', 'cable', 'Блок', 12)
ON CONFLICT (category, code) DO UPDATE
SET title_ru = EXCLUDED.title_ru;

INSERT INTO dictionaries (category, code, title_ru, sort_order) VALUES
    ('workout_level', 'beginner', 'Новичок', 1),
    ('workout_level', 'intermediate', 'Средний', 2),
    ('workout_level', 'advanced', 'Продвинутый', 3),

    ('fitness_goal', 'gain_muscle', 'Нарастить мышцы', 1),
    ('fitness_goal', 'strength', 'Сила', 2),
    ('fitness_goal', 'lose_weight', 'Сбросить вес', 3),
    ('fitness_goal', 'maintain', 'Поддержание формы', 4),
    ('fitness_goal', 'definition', 'Рельеф', 5),
    ('fitness_goal', 'flexibility', 'Гибкость', 6),
    ('fitness_goal', 'rehab', 'Реабилитация', 7),
    ('fitness_goal', 'endurance', 'Выносливость', 8),

    ('equipment', 'none', 'Нет', 1),
    ('equipment', 'dumbbells', 'Гантели', 2),
    ('equipment', 'kettlebell', 'Гиря', 3),
    ('equipment', 'plate', 'Диск', 4),
    ('equipment', 'bench', 'Скамья для жима', 5),
    ('equipment', 'machine', 'Машина', 6),
    ('equipment', 'gym', 'Тренажёрный зал', 7),
    ('equipment', 'other', 'Другое', 8),

    ('training_format', 'gym', 'В зале', 1),
    ('training_format', 'online', 'Онлайн', 2),
    ('training_format', 'hybrid', 'Онлайн + офлайн', 3),
    ('training_format', 'home', 'Дома', 4),
    ('training_format', 'visit', 'Выезд к клиенту', 5)
ON CONFLICT (category, code) DO NOTHING;

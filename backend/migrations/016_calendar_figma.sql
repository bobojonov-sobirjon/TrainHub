-- Figma «Добавить тренировки»: reminders none / 1h / 3h (+ optional 15m, 1d)
ALTER TABLE calendar_events DROP CONSTRAINT IF EXISTS calendar_events_reminder_check;
ALTER TABLE calendar_events
    ADD CONSTRAINT calendar_events_reminder_check
    CHECK (reminder IN ('none', '15m', '1h', '3h', '1d'));

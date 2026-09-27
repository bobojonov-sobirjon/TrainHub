ALTER TABLE exercises
    ADD COLUMN IF NOT EXISTS photo_urls TEXT[] NOT NULL DEFAULT '{}';

UPDATE exercises
SET photo_urls = ARRAY[photo_url]
WHERE photo_url IS NOT NULL
  AND photo_url <> ''
  AND (photo_urls IS NULL OR photo_urls = '{}');

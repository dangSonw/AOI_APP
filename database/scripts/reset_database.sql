-- Reset the entire AOI database
-- WARNING: This drops ALL data. Use only in development.

DROP TABLE IF EXISTS inspection_images CASCADE;
DROP TABLE IF EXISTS defects CASCADE;
DROP TABLE IF EXISTS inspection_results CASCADE;
DROP TABLE IF EXISTS recipes CASCADE;
DROP TABLE IF EXISTS users CASCADE;

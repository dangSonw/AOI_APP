-- Seed default recipes for the AOI system
INSERT INTO recipes (slug, name, description) VALUES
    ('rev-c-mainboard', 'Rev C · Mainboard', 'Main controller board revision C inspection recipe'),
    ('rev-b-power', 'Rev B · Power', 'Power supply board revision B inspection recipe'),
    ('rev-a-sensor', 'Rev A · Sensor', 'Sensor interface board revision A inspection recipe')
ON CONFLICT (slug) DO NOTHING;

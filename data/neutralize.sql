-- Clear Ebioro API credentials when the database is neutralized
-- (e.g. cloned to a staging/test environment) so non-production copies
-- never carry live keys. Odoo runs this automatically on neutralize.
UPDATE payment_provider
   SET ebioro_public_key = NULL,
       ebioro_secret_key = NULL
 WHERE code = 'ebioro';

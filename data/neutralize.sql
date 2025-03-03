-- disable stripe payment provider
UPDATE payment_provider
   SET ebioro_public_key = NULL,
       ebioro_secret_key = NULL;

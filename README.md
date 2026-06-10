# Ebioro Payment Provider for Odoo

Accept stablecoin (USDC) payments in Odoo through the Ebioro payments platform: payment processing, refunds, and signed webhook status updates.

## Branches

| Branch | Purpose |
|---|---|
| `development` | Active development — **targets Odoo 18** |
| `main` | Stable releases (Odoo 18) |
| `odoo_17` | Frozen legacy branch for Odoo 17 installs (no active maintenance) |

## Installation

### Prerequisites
- Odoo 18
- Python `requests` library (bundled with the official Odoo images; otherwise `pip install requests`)

### Steps
1. Clone the repository into your Odoo addons directory **as `payment_ebioro`** (the folder name matters — module imports reference it):
   ```sh
   git clone https://github.com/Ebioro-UAB/ebioro-odoo payment_ebioro
   ```
2. Restart Odoo and update the apps list (*Apps → Update Apps List*).
3. Install **Ebioro Payment Provider**.
4. Go to *Settings → Website / Accounting → Payment Providers → Ebioro*:
   - Set the state (*Test Mode* while integrating).
   - Enter your **API Key** and **API Secret** from the Ebioro portal (*Comercio → API para desarrolladores*; use the *test* key pair for Test Mode).
   - Publish the provider.

## Testing

The repo ships a throwaway local environment:

```sh
docker compose up -d        # Odoo 18 + Postgres on http://localhost:8069
```

1. Open http://localhost:8069, create a database (any name, demo data **on** — it gives you products to buy).
2. Install the **eCommerce** app, then **Ebioro Payment Provider** (*Apps → Update Apps List* first).
3. Configure the Ebioro provider as above with your **test** API keys, state = *Test Mode*, published.

### Webhooks need a public URL

Payment status updates arrive as signed webhooks from the Ebioro platform — they cannot reach `localhost`. Open a tunnel:

```sh
cloudflared tunnel --url http://localhost:8069     # or: ngrok http 8069
```

Then tell Odoo to use the tunnel URL when it builds redirect/webhook URLs:
*Settings → Technical → System Parameters* (developer mode):
- `web.base.url` → your tunnel URL (e.g. `https://random-name.trycloudflare.com`)
- add `web.base.url.freeze` = `True` (stops Odoo overwriting it on the next admin login)

### End-to-end test

1. Buy any product in the website shop and choose **Ebioro** at checkout.
2. You are redirected to the hosted payment page (`sandbox-pay.ebioro.com`) — pay with a test wallet.
3. The webhook flips the Odoo payment transaction (and sales order) state automatically.

**Debugging tip:** the Ebioro portal's *Comercio → Webhooks* tab shows every delivery attempt against your tunnel URL — status, HTTP code, payload, and a *Resend* button. If a webhook shows *Fallido*, the response body recorded there tells you what Odoo answered.

Reset everything with `docker compose down -v`.

## Support

- Issues: https://github.com/Ebioro-UAB/ebioro-odoo/issues
- Email: support@ebioro.com

## License

LGPL-3 — see the module manifest.

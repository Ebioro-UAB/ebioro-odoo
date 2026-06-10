# Ebioro Payment Provider for Odoo

Accept stablecoin (USDC) payments in your Odoo store through the [Ebioro](https://www.ebioro.com) payments platform. Customers are redirected to the Ebioro hosted payment page, and your orders update automatically via signed webhooks.

- **Odoo 18** (use the `main` / `development` branches)
- Redirect-based checkout — no card data touches your server
- HMAC-signed API requests and webhooks
- Works with Odoo eCommerce (website_sale) and any flow built on Odoo's `payment` module

## Requirements

- Odoo **18**
- The Python `requests` library (already bundled in the official Odoo Docker images; otherwise `pip install requests`)
- An Ebioro merchant account with API keys (sign up at [ebioro.com](https://www.ebioro.com))

## Installation

> **Important:** the module folder **must** be named `payment_ebioro`. Odoo identifies modules by folder name and the code imports `odoo.addons.payment_ebioro` — a different folder name will fail to install.

1. **Place the module in your Odoo addons path as `payment_ebioro`:**
   ```sh
   cd /path/to/your/odoo/addons
   git clone https://github.com/Ebioro-UAB/ebioro-odoo payment_ebioro
   ```
   (Or download a release zip and extract it as a folder named `payment_ebioro`.)

2. **Restart Odoo** and update the apps list: *Apps → Update Apps List*.

3. **Install the module:** search **Ebioro Payment Provider** in *Apps* and click *Install*.
   For an online shop, also install **eCommerce** (`website_sale`).

## Configuration

1. Go to *Settings → Payments → Payment Providers* (or *Website → Configuration → Payment Providers*) and open **Ebioro**.
2. Set the **State**:
   - **Test Mode** while you integrate (uses the Ebioro sandbox).
   - **Enabled** for live payments.
3. In the **Credentials** tab, enter your **API Key** and **API Secret** from the Ebioro portal
   (*Comercio → API para desarrolladores*). Use the **test** key pair while in Test Mode, the **live** pair when Enabled.
4. **Publish** the provider so it appears at checkout.

That's it — "Pay with crypto" now shows as a payment option at checkout.

## How it works

1. At checkout the module calls the Ebioro API and redirects the customer to the hosted payment page.
2. The customer pays with their stablecoin wallet.
3. Ebioro sends signed webhooks to your store; the module verifies the signature and updates the payment transaction and order automatically.

### Refunds

Refunds are **not** issued from Odoo. Ebioro is non-custodial — settled funds land on your own account, so a refund moves your funds and must be signed by you. Issue refunds from the **Ebioro enterprise portal** (*Comercio → open the payment → Refund*), where your signing session is available.

## Local testing

The repo ships a throwaway Docker environment:

```sh
docker compose up -d        # Odoo 18 + Postgres on http://localhost:8069
```

1. Open http://localhost:8069, create a database (demo data **on** gives you products to buy).
2. Install **eCommerce**, then **Ebioro Payment Provider**.
3. Configure the Ebioro provider with your **test** API keys, State = *Test Mode*, published.

### Webhooks need a public URL

Webhooks from Ebioro can't reach `localhost`, so open a tunnel:

```sh
cloudflared tunnel --url http://localhost:8069     # or: ngrok http 8069
```

Then point Odoo at the tunnel — *Settings → Technical → System Parameters* (developer mode):
- `web.base.url` → your tunnel URL
- `web.base.url.freeze` = `True` (stops Odoo overwriting it on the next admin login)

### End-to-end

Buy a product, choose **Ebioro**, pay on `sandbox-pay.ebioro.com` with a test wallet. The webhook flips the order to paid automatically. The Ebioro portal's *Comercio → Webhooks* tab shows every delivery (status, HTTP code, payload, resend) — your debugging surface if a webhook fails.

Reset everything with `docker compose down -v`.

## Support

- Issues: https://github.com/Ebioro-UAB/ebioro-odoo/issues
- Security reports: see [SECURITY.md](SECURITY.md)
- Email: support@ebioro.com

## License

[LGPL-3](LICENSE).

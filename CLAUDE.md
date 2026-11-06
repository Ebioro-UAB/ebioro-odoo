# ebioro-odoo

Odoo 18 payment provider module for Ebioro hosted checkout (public repository, LGPL-3). Installs as `payment_ebioro`; at checkout the customer is redirected to the Ebioro-hosted payment page, and a signed webhook updates the `payment.transaction` and the order. Thin client of the Ebioro merchant public API — same HMAC signing, hosted checkout, and webhook contract as `ebioro-payment-woocommerce` and `ebioro-payment-prestashop`; a gotcha in one usually applies to all three.

## Architecture
- `models/payment_provider.py` — provider record, credentials, state (`test` = sandbox, `enabled` = production; base URLs in `const.py`).
- `models/payment_transaction.py` — creates the payment (HMAC `X-Digest-*` headers), maps statuses, handles notification data. Refunds are intentionally not implemented (see Gotchas).
- `controllers/main.py` — webhook endpoint (HMAC-SHA256 over the raw body, `hmac.compare_digest`) and the customer return route.
- `const.py` — API URLs by provider state, supported currencies, status mapping.

## Dev commands
- `docker compose up -d` — Odoo 18 + Postgres on http://localhost:8069. Install **eCommerce** then **Ebioro Payment Provider**; configure test keys, State = Test Mode, publish.
- Webhooks need a public URL: `cloudflared tunnel --url http://localhost:8069`, then set `web.base.url` to the tunnel and `web.base.url.freeze = True` (developer mode → System Parameters) — otherwise Odoo overwrites the URL on the next admin login.

## Gotchas
- **The module folder must be named `payment_ebioro`.** Odoo identifies modules by folder name and the code imports `odoo.addons.payment_ebioro`; any other folder name fails to install.
- **Status-mapping values in `const.py` are tuples on purpose.** A bare string makes `status in (...)` do substring matching (`'paid' in 'unpaid'` is true).
- **The return route (`/payments/ebioro/return`) is unauthenticated and must never change transaction state.** Only the verified webhook does. Don't log its full query string either — it carries payment identifiers.
- **Redirect with `shortUrl`, falling back to `hostedUrl`** — the hosted URL carries an auth token in its query string.
- **Refunds are not done from Odoo.** Settled funds sit on the merchant's own account, so a refund must be signed by the merchant in the Ebioro portal. Don't add a refund action here.
- Digest headers are redacted in logs (`X-Digest-Key` / `X-Digest-Signature`); keep it that way when adding logging.

<!-- BEGIN ebioro-non-negotiables v2 — master: Ebioro-UAB/documentation -->
## Ebioro non-negotiables

- **GitHub text hygiene — the KU corridor country is never named.** In any
  GitHub-visible text (commit messages, PR titles/bodies, reviews, issues,
  branch names, release notes, code/spec comments) write `KU` — never the
  country's name, demonym, or capital. The ISO code `CU` as functional data
  (string literals, catalog entries, `=== 'CU'` checks) and full-country
  datasets (countries.json, i18n locales) are fine. End-user UI strings may
  carry the real name; keep those literals minimal. Scrub old text on touch.
- **Never merge or push to `main`, never tag a production release, never deploy.**
  Open the PR and stop. Merges and deploys are human-only — no exception for
  "the review passed" or "it's just a patch bump". Never delete `main`,
  `master`, or `development`.
- **Never commit `.env` or any file containing a secret.** `.gitignore` covers
  `.env*` with `.env.example` as the only tracked variant. A secret that lands
  in git is leaked even after the file is removed — rotate it.
- **No AI attribution in git or GitHub text.** No `Co-Authored-By:` lines, no
  "Generated with …" footers in commits, PR bodies, or issues.
- **Error handling: `neverthrow` Result types. Never `try/catch`.**
- **TypeORM migrations: snake_case column identifiers only.** Quoting
  `"customerId"` preserves camelCase; TypeORM then queries `customer_id` and
  crashes at runtime. `build` does not catch it. This has cost two fix
  migrations already.
- **Follow the existing flow in code, not design docs or mockups.** Find the
  nearest equivalent already implemented and match it. Design notes are
  proposals.
- **Money paths**: integer stroops/cents, never floats. Idempotency keys on
  anything that moves money. Stellar sequence numbers fetched fresh. Never log
  or expose a signing key or an API secret.
- **Ebioro never holds keys for customer funds.** Before creating any key or
  account, ask whose funds it will hold. If a customer's, it cannot be a key
  Ebioro can use alone.
- **User-facing copy hides blockchain jargon.** "Payment reference", not
  "transaction hash". "Settled", not "confirmed on ledger N". "Network fee",
  not "XLM base fee". No signing-vendor names. It should read like a bank app,
  not a block explorer.
- **No regulatory claims** in user-facing text — not "licensed", "registered",
  "authorised", "MiCAR-compliant", or any variant. Route legal-sounding copy
  through Ebioro before merging.
- **Soft-delete only** (`deletedAt`). Never hard-delete.
- **Never skip pre-commit hooks** (`--no-verify`). Flag new dependencies in the
  PR description.
- **Never paste production data, customer PII, credentials, or KYC/AML content
  into an AI tool.** Anonymised or synthetic only.
<!-- END ebioro-non-negotiables v2 -->

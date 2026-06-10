# Security Policy

## Supported Versions

Only the latest release on the `main` branch (Odoo 18) receives security updates.

## Reporting a Vulnerability

Please **do not open a public GitHub issue** for security vulnerabilities.

Report them privately to **support@ebioro.com** with:

- A description of the issue and its impact
- Steps to reproduce (a proof of concept helps)
- The module version and the Odoo version involved

We will acknowledge your report within 5 business days and keep you informed while we work on a fix. Please give us reasonable time to release a fix before any public disclosure.

## Scope

This policy covers the code in this repository (the Odoo payment module). Vulnerabilities in the Ebioro platform itself should also be reported to support@ebioro.com.

## Handling of credentials

- API keys are stored on the `payment.provider` record; the secret key is masked in the UI.
- The module never logs API keys, signatures, or auth tokens at INFO level (debug-only).
- `data/neutralize.sql` clears the stored API keys when an Odoo database is neutralized (e.g. cloned to staging), so non-production copies don't carry live credentials.

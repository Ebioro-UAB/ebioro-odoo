# Ebioro Payment Provider for Odoo

This module integrates the Ebioro payment provider with Odoo, supporting digital asset payments and refunds.

## Features
- Payment processing via Ebioro API
- Refunds via Ebioro API
- HMAC authentication for all API calls
- Odoo 18 compatible (use this branch)

## Installation

### Prerequisites
- Odoo 18 installed
- Python dependencies: requests, hmac, hashlib (requests is not included by default in Odoo, install with `pip install requests` if needed)

### Steps
1. **Clone the repository** into your Odoo addons directory:
   ```sh
   git clone <your-repo-url> payment_ebioro
   ```
2. **Checkout the odoo_18_structure_fix branch**:
   ```sh
   git checkout odoo_18_structure_fix
   ```
3. **Install Python dependencies** (if not already available):
   ```sh
   pip install requests
   ```
4. **Update Odoo Apps List**:
   - Go to Apps in Odoo backend
   - Click 'Update Apps List'
5. **Install the Ebioro Payment Provider module** from the Apps menu.

## Configuration
1. Go to **Invoicing > Configuration > Payment Providers** in Odoo.
2. Select or create the Ebioro provider.
3. Enter your Ebioro API Public Key and Secret Key (test or live as needed).
4. Set the provider to 'Test' or 'Production' mode as appropriate.
5. Save the configuration.

## Usage
- Create a payment using the Ebioro provider.
- Refunds can be triggered from the payment transaction or related invoice.
- All API requests and responses are logged for troubleshooting.

## Notes
- Make sure your Odoo server can reach the Ebioro API endpoints.
- Webhooks must be accessible from the internet for live payment notifications.

## Support
For issues or questions, contact the module maintainer or open an issue in the repository.

# Exchange Rate Sync

## Overview
**Exchange Rate Sync** is a Frappe app that automatically retrieves and updates currency exchange rates in your Frappe/ERPNext site using the [Open Exchange Rates](https://openexchangerates.org) API.  The app provides both automated daily updates and manual on-demand updates.

---

## Features
- **Automated Daily Sync** – Updates exchange rates daily for user configured currencies.
- **Manual Update** – An **Update Exchange Rates** button to fetch the latest rates instantly.
- **Multiple Base Currencies (Paid Plan)** – On the **Paid** API plan, base currencies are customizable. On the **Free** plan, the base is fixed to **USD**. 
- **Custom Target Currencies** – Select any number of target currencies.
- **Cross Exchange Rate Conversion** – When enabled, exchange rates **between** all *Target* currencies are calculated by using **USD as a bridge currency**.  
- **Automated Monthly Cleanup** – Deletes old exchange rates at month-end to keep the database lean.

---

## Installation

### Prerequisites

- Frappe Framework installed
- API key from [Open Exchange Rates](https://  openexchangerates.org/)


### Steps to Install

1. Clone the repository into your apps directory:
   ```bash
   bench get-app exchange_rate_sync https:// github.com/DeliveryDevs-ERP/Exchange-Rate-Sync.git
   ```
2. Install the app on your site:
   ```bash
   bench --site your-site-name install-app exchange_rate_sync
   ```

## Usage
1. Access the **Exchange Rate Config** doctype via the desk in your Frappe instance.

2. Enable the configuration and enter your API key. Click on **Test Connection** to validate the key and load plan details.

3. Configure your desired currencies in “From Currency” and “To Currency” tables. 

4. Click **Update Exchange Rates** for an immediate update, or let the **daily scheduler** update them automatically.

5. Go to **Currency Exchange List** doctype to view the saved rates.

### Contributing

We welcome contributions! Please submit a pull request with a detailed description of your changes.

## License

This project is licensed under the MIT License.
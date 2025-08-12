# Exchange Rate Sync

## Overview
**Exchange Rate Sync** is a Frappe app that automatically retrieves and updates currency exchange rates from [Open Exchange Rates](https://openexchangerates.org) using their API.  
The app provides both automated daily updates and manual on-demand updates through the **Exchange Rate Config** DocType.

---

## Features
- **Automated Daily Sync:** Updates currency exchange rates every day based on the configured currencies.
- **Manual Update:** An **Update Exchange Rates** button in the **Exchange Rate Config** DocType to fetch the latest rates instantly.
- **Multiple Base Currencies (Paid Plan):** If the user is on a paid Open Exchange Rates plan, the **From Currency Table** becomes editable to allow setting any base currency. For the free plan, the base currency is limited to **USD**.
- **Custom Target Currencies:** Choose specific currencies in the **To Currency Table** to retrieve conversion rates for.
- **Connection Test:** Verify your API key and see your plan details and quota.
- **Monthly Cleanup:** Automatically deletes exchange rates older than yesterday to keep the database clean.

---

## Requirements
- **Frappe Framework** v15+
- API key from [Open Exchange Rates](https://openexchangerates.org/)

---

## Installation
From your Frappe/ERPNext bench folder:
```bash
bench get-app exchange_rate_sync https://github.com/DeliveryDevs-ERP/Exchange-Rate-Sync.git
bench --site your-site-name install-app exchange_rate_sync
```

---

## Configuration

1. Go to **Exchange Rate Config** in your Frappe site.
2. Enable the configuration.
3. Enter your **Open Exchange Rates API Key**.
4. For **Free Plan**:
   - **From Currency Table** is locked to USD.
   - Only **To Currency Table** is editable.
5. For **Paid Plan**:
   - **From Currency Table** is editable, allowing you to select multiple base currencies.
6. Use the **Test Connection** button to validate your API key and update plan details.

---

## Automated Sync
- Runs **daily** using the scheduler.
- Retrieves rates for each base currency against each target currency.
- Inserts or updates both **Base → Target** and **Target → Base** exchange rates in the `Currency Exchange` DocType.

---

## Manual Update
- Click **Update Exchange Rates** in the Exchange Rate Config DocType to fetch latest rates immediately. This button is hidden by default. To make it visible, edit the doctype and change the "hidden" property of this field.
- The process uses the same logic as the automated sync but is triggered manually.

---

## API Calls & Limits
- **Free Plan:** Base currency restricted to USD.
- **Paid Plan:** Any currency can be used as base.
- The app logs errors for non-200 responses and missing configuration data.
- Default retry delay is **1 second** between API calls.

---

## Monthly Cleanup
- Once a month, exchange rates older than yesterday are deleted to keep the database lightweight.

---

## Scheduler Events
| Frequency | Function |
|-----------|----------|
| Daily     | `exchange_rate_sync.tasks.daily.get_currency_exchange` |
| Monthly   | `exchange_rate_sync.tasks.monthly.delete_currency_exchange_monthly` |

---
## Troubleshooting

### “Please test the connection first”
Ensure **Enabled** is checked and you’ve clicked **Test Connection**.  
The form must not be dirty.

### Non-USD base fails on Free plan
With OXR Free, the base must be **USD**.  
Use USD in the *From Currency* table or upgrade your OXR plan.

### New rows in *To Currency* table default to PKR
Remove any default on the child field or ensure your client script clears it  
(project includes logic to manage grid behavior).

### No rates written
Confirm *From* and *To* tables aren’t empty.  
The sync will return messages like:
- `No base currencies configured in From Currency Table`
- `No target currencies configured in To Currency Table`

### Stale data volume
Monthly cleanup removes entries older than yesterday automatically.

---

## Developer Notes

###  Directory Structure

```
exchange_rate_sync/
├── exchange_rate_sync/
│   ├── exchange_rate_sync/         
│       └── doctype/    
│           └── exchange_rate_config/
│               └── exchange_rate_config.js   # Frontend logic for saving new base currency and update button
├── tasks/
│   └── api.py           # For calling backend functions in Exchange Rate Config doctype
│   ├── daily.py         # Daily exchange rate update function
│   └── monthly.py       # Monthly cleanup task
├── hooks.py             # Scheduler configuration 
└── README.md            # Project documentation
```

---

### Key Files

#### `tasks/api.py`
- **`test_connection()`** — validates API key via OXR usage endpoint; updates plan/quota/status and sets `from_currency_option` (*USD Only* vs *All Currencies*).
- **`get_api_usage_info(api_key)`** — returns live usage metrics for the **API Usage Info** button.
- **`get_currency_exchange_ui()`** — thin wrapper for UI button calling the daily sync.

#### `tasks/daily.py`
- **`get_currency_exchange()`** — core sync logic:
  - Reads `api_key` + currency tables from *Exchange Rate Config*.
  - Calls OXR `latest.json` for each base.
  - Upserts *Currency Exchange* in both directions.
  - Minimal retry, 1s delay between attempts (`DELAY_SEC`).
  - Returns a human-readable summary string.

#### `tasks/monthly.py`
- **`delete_currency_exchange_monthly()`** — deletes rows with `date` < yesterday.

#### `doctype/Exchange Rate Config/exchange_rate_config.js`
- **UI behavior**:
  - Toggles visibility & read-only by `enabled`, `connection_success`, and `from_currency_option`.
  - Handles **Test Connection**, **API Usage Info**, and **Update Exchange Rates** actions.
  - Guards to prevent actions while the form is dirty.

---

### Behavior Toggles (Front-End)
- **`api_usage_info`** shown when `enabled && connection_success == 1`.
- **`update_exchange_rates`** shown when `enabled && connection_success == 1`.
- **`to_currency_table`** editable when `enabled && connection_success == 1`.
- **`from_currency_table`**:
  - Read-only when `from_currency_option == "USD Only"`.
  - Editable when `from_currency_option == "All Currencies"`.

---

### Notes on Delays & Retries
- `DELAY_SEC = 1` (in `daily.py`) — simple pacing between network attempts and per-base loops.
- Adjust if needed.

---

### What Gets Written
**DocType:** *Currency Exchange* (core ERPNext):
- `date`: today.
- `from_currency`: each base you configured.
- `to_currency`: each target you configured (excluding base).
- `exchange_rate`:
  - **Direct**: value from `OXR rates[to_currency]`.
  - **Reverse**: `round(1 / rate, 10)`.

The app **upserts** rows (updates existing if found for the same date & currency pair, otherwise inserts new ones).

---

## Error Handling
The app will:
- Log an error in Frappe's error log if the API key is missing, tables are empty, or the API returns an error.
- Return a message to the UI in case of connection failure or missing data.

---

## License
MIT License 

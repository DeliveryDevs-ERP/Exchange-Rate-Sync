# Exchange Rate Sync App for Frappe

This is a custom Frappe app that allows you to fetch and manage exchange rates via a third-party API and maintain up-to-date currency exchange data in your ERP system.
---

## Purpose

- Automatically fetch and insert daily exchange rates for enabled currencies in the **Currency Exchange** DocType.
- Clean up old exchange rates monthly to keep your database light.
- Requires no manual data entry.

---

## How It Works

### 1. `exchange_rate_config.js`
- Allows user so select base currency.
- Adds a button (`update_exchange_rates`) in the Exchange Rate Config Doctype
- On click:
  - Saves the form if dirty
  - Calls the server-side method `get_currency_exchange_from_ui`
  - Displays appropriate success or error message
  - Also has an `after_save` hook that auto-fetches rates when saved (unless triggered from button)

### 2. `daily.py` — Insert Daily Currency Exchange Rates

- Fetches the **default base currency** from **Exchange Rate Config**.
- Gets all **enabled currencies** from the `Currency` DocType.
- Calls the external API ([exchangerate.host](https://exchangerate.host)) to get exchange rates for the enabled currencies.
- Inserts two-way exchange rates:
  - BASE → OTHER
  - OTHER → BASE

**Example**  
If the base currency is `PKR` and the rate for `PKRAED` is `0.0131`, the following records are created:
- PKR → AED at `0.0131`
- AED → PKR at `1 / 0.0131`

---

### 3. `monthly.py`
- Defines `delete_currency_exchange_monthly` function
- Deletes `Currency Exchange` records older than yesterday
- Runs as a scheduled task
> You can enhance this later to delete only old records instead of wiping all.

---

##  Scheduled Jobs (hooks.py)

- [daily] - Inserts new exchange rates daily.
- [monthly] - Deletes old records once a month.

##  Setup Instructions

### 1. Install the App

```bash
bench get-app exchange_rate_sync
bench --site your-site-name install-app exchange_rate_sync
```

### 2. Enable Scheduler

```bash
bench --site your-site-name set-config enable_scheduler 1
bench enable-scheduler
```

---

##  Supported APIs

###  exchangerate.host

- Flexible base currency support
- 100 requests/month on free tier
- Example API call:
  ```
  https://api.exchangerate.host/live?access_key=YOUR_KEY&source=PKR&currencies=AED,USD
  ```

###  Optional: openexchangerates.org

- Base currency is always **USD**
- 1000 requests/month on free tier
- Toggle by uncommenting the alternate code block in `daily.py`
- Example API call:
  ```
  https://openexchangerates.org/api/latest.json?app_id=YOUR_KEY&symbols=AED,EUR
  ```

---

##  Error Handling

All major errors are logged to the Frappe error log:

- `"Exchange Rate Sync"`
- `"Monthly Currency Exchange Deletion Failed"`

---

##  Directory Structure

```
exchange_rate_sync/
├── exchange_rate_sync/
│   ├── exchange_rate_sync/         
│       └── doctype/    
│           └── exchange_rate_config/
│               └── exchange_rate_config.js   # Frontend logic for saving new base currency and update button
├── tasks/
│   ├── daily.py         # Daily exchange rate update function
│   └── monthly.py       # Monthly cleanup task
├── hooks.py             # Scheduler configuration 
└── README.md            # Project documentation
```

---




##  License

MIT License
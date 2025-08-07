# Exchange Rate Sync App for Frappe
# Exchange Rate Sync

**Exchange Rate Sync** is a custom Frappe app that automates the retrieval and management of currency exchange rates using the [exchangerate.host API](https://exchangerate.host/). It allows users to:

- Add base currencies for which exchange rates should be fetched.
- Automatically sync daily exchange rates.
- Update exchange rates manually.
- Clean up old exchange rate records monthly.

## 🔧 Features

### 📅 Daily Exchange Rate Sync
- A daily scheduled task (defined in `daily.py`) fetches exchange rates for all saved base currencies.
- Only enabled currencies are considered as valid target currencies.
- Exchange rates are fetched from exchangerate.host API.
- Existing exchange rates for the same day are **updated**, not duplicated.
- Inserts two-way exchange rates:
  - BASE → OTHER
  - OTHER → BASE

**Example**  
If the base currency is `PKR` and the rate for `PKRAED` is `0.0131`, the following records are created:
- PKR → AED at `0.0131`
- AED → PKR at `1 / 0.0131`

### 🗑️ Monthly Cleanup
- A monthly scheduled task (defined in `monthly.py`) deletes all currency exchange records **older than yesterday**, to avoid cluttering the database.

---

## 🧾 Exchange Rate Config Doctype

The `Exchange Rate Config` Doctype provides a user interface for managing base currencies and controlling exchange rate sync actions.

### Fields:
- **Exchange Rate List (Table):** Displays all base currencies currently being tracked.

### Actions:
- **Add:**  
  Adds a new base currency to the Table. Automatically fetches and stores exchange rates for the selected base currency.
  
- **Remove:**  
  Removes a base currency from the Table. Does **not** delete historical exchange rates for that currency.
  
- **Update:**  
  Updates exchange rates for:
  - A specific base currency selected from the dropdown.
  - All saved base currencies by choosing `All` from the dropdown.

---

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

###  API Information

##  exchangerate.host

- Flexible base currency support
- 100 requests/month on free tier
- Example API call:
  ```
  https://api.exchangerate.host/live?access_key=YOUR_KEY&source=PKR&currencies=AED,USD
  ```

##  Optional: openexchangerates.org

- Base currency is always **USD**
- 1000 requests/month on free tier
- Toggle by uncommenting the alternate code block in `daily.py` and `api.py`
- Example API call:
  ```
  https://openexchangerates.org/api/latest.json?app_id=YOUR_KEY&symbols=AED,EUR
  ```

---

## Best Practices

Always monitor API usage if using the free tier.

Manually trigger updates using the Update button when needed.

Review error logs for failed API calls (handled using frappe.log_error).

##  Directory Structure

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

##  License

MIT License


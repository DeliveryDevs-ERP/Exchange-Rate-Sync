


import time
import requests
import frappe
from frappe.utils import today

OXR_LATEST_URL = "https://openexchangerates.org/api/latest.json"
DELAY_SEC = 1  # fixed delay between API requests/retries (change in code later if needed)

def _req_with_retry(url: str, params: dict, retries: int = 3, delay_sec: int = DELAY_SEC):
    """
    Do a GET with minimal retry on network errors or non-200 responses.
    Returns (json_dict, status_code). On total failure returns (None, status_code_or_None).
    """
    last_status = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=15)
            last_status = resp.status_code
            if resp.status_code == 200:
                return resp.json(), 200
            else:
                frappe.log_error(
                    title="Exchange Rate Sync: API non-200",
                    message=f"Attempt={attempt}\nParams={params}\nStatus={resp.status_code}\nBody={resp.text[:2000]}"
                )
        except requests.exceptions.RequestException as e:
            frappe.log_error(
                title="Exchange Rate Sync: RequestException",
                message=f"Attempt={attempt}\nParams={params}\nError={e}"
            )
            last_status = None

        if attempt < retries:
            time.sleep(delay_sec)

    return None, last_status

def get_currency_exchange():
    """
    Fetch rates from Open Exchange Rates for:
      - each base currency in 'from_currency_table'
      - target currencies in 'to_currency_table'
    API key is read from 'Exchange Rate Config.api_key'.

    Returns a human-readable string describing the outcome.
    """
    # Load config single
    try:
        cfg = frappe.get_doc("Exchange Rate Config", "Exchange Rate Config")
    except Exception as e:
        frappe.log_error("Exchange Rate Sync: Failed to load config", str(e))
        return "Failed to load Exchange Rate Config"

    api_key = (cfg.api_key or "").strip()
    if not api_key:
        frappe.log_error("Exchange Rate Sync", "Missing API key in Exchange Rate Config")
        return "Missing API key in Exchange Rate Config"

    # Collect base and target currencies from child tables
    base_currencies = [
        (row.from_currency or "").strip().upper()
        for row in (cfg.get("from_currency_table") or [])
        if (row.from_currency or "").strip()
    ]
    target_currencies = [
        (row.to_currency or "").strip().upper()
        for row in (cfg.get("to_currency_table") or [])
        if (row.to_currency or "").strip()
    ]

    if not base_currencies:
        frappe.log_error("Exchange Rate Sync", "No base currencies configured")
        return "No base currencies configured in From Currency Table"
    if not target_currencies:
        frappe.log_error("Exchange Rate Sync", "No target currencies configured")
        return "No target currencies configured in To Currency Table"

    results = []
    success_count = 0
    fail_count = 0
    today_str = today()

    for i, base in enumerate(base_currencies, start=1):
        # exclude base from targets for this request
        symbols = [c for c in target_currencies if c and c != base]
        if not symbols:
            results.append(f"Skipped {base}: no target currencies after excluding base.")
            continue

        params = {
            "app_id": api_key,
            "base": base,                      # NOTE: non-USD base requires paid plan
            "symbols": ",".join(symbols),
        }

        data, status = _req_with_retry(OXR_LATEST_URL, params=params, retries=2, delay_sec=DELAY_SEC)

        if status is None:
            msg = f"Network error while fetching rates for base {base}"
            frappe.log_error("Exchange Rate Sync", msg)
            results.append(msg)
            fail_count += 1
            time.sleep(DELAY_SEC)
            continue

        if status != 200:
            msg = f"API request failed for base {base} with status code {status}"
            # Common cause: Free plan only supports USD base; non-USD will return 400/403
            frappe.log_error("Exchange Rate Sync", f"{msg}\nParams={params}")
            results.append(msg)
            fail_count += 1
            time.sleep(DELAY_SEC)
            continue

        rates = (data or {}).get("rates") or {}
        if not rates:
            msg = f"No rates returned for base {base}"
            frappe.log_error("Exchange Rate Sync", f"{msg}\nBody={data}")
            results.append(msg)
            fail_count += 1
            time.sleep(DELAY_SEC)
            continue

        # Upsert both directions for today's date
        updated_pairs = 0
        for to_currency, rate in rates.items():
            try:
                if not rate:
                    continue

                # BASE -> OTHER
                existing = frappe.db.get_value(
                    "Currency Exchange",
                    {
                        "date": today_str,
                        "from_currency": base,
                        "to_currency": to_currency
                    },
                    "name"
                )
                if existing:
                    frappe.db.set_value("Currency Exchange", existing, "exchange_rate", rate)
                else:
                    frappe.get_doc({
                        "doctype": "Currency Exchange",
                        "date": today_str,
                        "from_currency": base,
                        "to_currency": to_currency,
                        "exchange_rate": rate
                    }).insert(ignore_permissions=True)

                # OTHER -> BASE (inverse)
                reverse_rate = round(1 / rate, 10)
                reverse_name = frappe.db.get_value(
                    "Currency Exchange",
                    {
                        "date": today_str,
                        "from_currency": to_currency,
                        "to_currency": base
                    },
                    "name"
                )
                if reverse_name:
                    frappe.db.set_value("Currency Exchange", reverse_name, "exchange_rate", reverse_rate)
                else:
                    frappe.get_doc({
                        "doctype": "Currency Exchange",
                        "date": today_str,
                        "from_currency": to_currency,
                        "to_currency": base,
                        "exchange_rate": reverse_rate
                    }).insert(ignore_permissions=True)

                updated_pairs += 1

            except Exception as e:
                frappe.log_error(
                    title="Exchange Rate Sync: Upsert error",
                    message=f"Base={base} To={to_currency}\nError={e}"
                )

        frappe.db.commit()
        success_count += 1
        results.append(f"Updated {updated_pairs} pairs for base {base}.")
        time.sleep(DELAY_SEC)

    if fail_count and not success_count:
        return "Exchange rate sync failed for all bases:\n" + "\n".join(results)
    elif fail_count:
        return f"Exchange rate sync completed with issues ({success_count} succeeded, {fail_count} failed):\n" + "\n".join(results)
    else:
        return "Exchange rate sync completed successfully."




## For use with different API Provider
# def get_currency_exchange():
#     URL = "https://api.exchangerate.host/live"
#     API_KEY = os.getenv("API_KEY_EXCHANGERATEHOST")
#     # Get enabled currencies (excluding base)
#     enabled_currencies = frappe.get_all(
#         "Currency",
#         filters={"enabled": 1},
#         pluck="name"
#     )
#     if not enabled_currencies:
#         frappe.log_error("No enabled currencies found", "Exchange Rate Sync")
#         return
    
#     doc = frappe.get_doc("Exchange Rate Config", "Exchange Rate Config")

#     # Determine base currencies to process       
#     base_currencies = [row.currency for row in doc.base_currency_list]
#     if not base_currencies:
#         frappe.log_error("No base currencies configured", "Exchange Rate Sync")
#         return

#     for base_currency in base_currencies:
#         target_currencies = [c for c in enabled_currencies if c != base_currency]
#         if not target_currencies:
#             frappe.log_error(f"No target currencies for base {base_currency}", "Exchange Rate Sync")
#             continue

#         # Prepare API params
#         params = {
#             "access_key": API_KEY,
#             "source": base_currency,
#             "currencies": ",".join(target_currencies)
#         }


#         response = requests.get(URL, params=params)
#         data = response.json()

#         if not data.get("success"):
#             frappe.log_error(f"API error for {base_currency}: {response.text}", "Exchange Rate Sync")
#             continue

#         quotes = data.get("quotes", {})
#         for pair, rate in quotes.items():
#             if not pair.startswith(base_currency) or rate == 0:
#                 continue

#             to_currency = pair.replace(base_currency, "")

#             # Update or insert BASE → OTHER
#             doc1 = frappe.db.get_value("Currency Exchange", {
#                 "date": today(),
#                 "from_currency": base_currency,
#                 "to_currency": to_currency
#             }, "name")
#             if doc1:
#                 frappe.db.set_value("Currency Exchange", doc1, "exchange_rate", rate)
#                 frappe.db.commit()

#             else:
#                 new_doc1 = frappe.get_doc({
#                     "doctype": "Currency Exchange",
#                     "date": today(),
#                     "from_currency": base_currency,
#                     "to_currency": to_currency,
#                     "exchange_rate": rate
#                 })
#                 new_doc1.insert(ignore_permissions=True)
#                 frappe.db.commit()

#             # Update or insert OTHER → BASE
#             reverse_doc = frappe.db.get_value("Currency Exchange", {
#                 "date": today(),
#                 "from_currency": to_currency,
#                 "to_currency": base_currency
#             }, "name")

#             reverse_rate = round(1 / rate, 6)
#             if reverse_doc:
#                 frappe.db.set_value("Currency Exchange", reverse_doc, "exchange_rate", reverse_rate)
#                 frappe.db.commit()

#                 print(reverse_doc)
#             else:
#                 new_doc2 = frappe.get_doc({
#                     "doctype": "Currency Exchange",
#                     "date": today(),
#                     "from_currency": to_currency,
#                     "to_currency": base_currency,
#                     "exchange_rate": reverse_rate
#                 })
#                 new_doc2.insert(ignore_permissions=True)
#                 frappe.db.commit()
#         time.sleep(1)

#     return True

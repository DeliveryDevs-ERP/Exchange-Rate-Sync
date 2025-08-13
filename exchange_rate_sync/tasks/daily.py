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


def cross_pair_with_usd(date_str: str, a: str, b: str, usd_rates: dict) -> int:
    """
    Using USD-based rates:
      rate(a->b) = (USD->b) / (USD->a)
    Upserts a->b and b->a for given date.
    Returns 1 if forward (a->b) was updated/inserted; 0 if skipped.
    """
    ra = usd_rates.get(a)
    rb = usd_rates.get(b)
    if not ra or not rb or ra <= 0 or rb <= 0:
        return 0

    rate_ab = rb / ra
    if rate_ab <= 0:
        return 0

    # a -> b
    name = frappe.db.get_value(
        "Currency Exchange",
        {"date": date_str, "from_currency": a, "to_currency": b},
        "name",
    )
    if name:
        frappe.db.set_value("Currency Exchange", name, "exchange_rate", rate_ab)
    else:
        frappe.get_doc({
            "doctype": "Currency Exchange",
            "date": date_str,
            "from_currency": a,
            "to_currency": b,
            "exchange_rate": rate_ab
        }).insert(ignore_permissions=True)

    # b -> a (inverse)
    rate_ba = 1 / rate_ab
    rev_name = frappe.db.get_value(
        "Currency Exchange",
        {"date": date_str, "from_currency": b, "to_currency": a},
        "name",
    )
    if rev_name:
        frappe.db.set_value("Currency Exchange", rev_name, "exchange_rate", rate_ba)
    else:
        frappe.get_doc({
            "doctype": "Currency Exchange",
            "date": date_str,
            "from_currency": b,
            "to_currency": a,
            "exchange_rate": rate_ba
        }).insert(ignore_permissions=True)

    return 1


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
    try:
        cfg = frappe.get_doc("Exchange Rate Config", "Exchange Rate Config")
    except Exception as e:
        frappe.log_error("Exchange Rate Sync: Failed to load config", str(e))
        return "Failed to load Exchange Rate Config"

    # Run only if enabled
    if cfg.enabled == 0:
        frappe.log_error("Exchange Rate Sync", "sync not enabled")
        return "Exchange rate sync is disabled in Exchange Rate Config"
    
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

    # NEW: capture USD-based rates from the USD iteration (for cross conversions after the loop)
    usd_rates_for_cross = None

    for i, base in enumerate(base_currencies, start=1):
        # exclude base from targets for this request
        symbols = [c for c in target_currencies if c and c != base]
        if not symbols:
            results.append(f"Skipped {base}: no target currencies after excluding base.")
            continue

        params = {
            "app_id": api_key,
            "base": base,                      # note: non-USD base requires paid plan
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

        # NEW: if this is the USD iteration, keep its USD->X rates to do cross conversions later
        if base == "USD":
            usd_rates_for_cross = rates.copy()
            usd_rates_for_cross.setdefault("USD", 1.0)
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
                reverse_rate = 1 / rate
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

    # NEW: After the loop, if cross_rate_conversion enabled, compute cross rates among to_currency_table via USD
    try:
        if getattr(cfg, "cross_rate_conversion", 0):
            if not usd_rates_for_cross:
                frappe.log_error(
                    "Exchange Rate Sync",
                    "Cross conversion enabled but USD rates are unavailable (no successful USD iteration). Skipping cross conversions."
                )
                results.append("Cross conversion skipped: USD rates unavailable.")
            else:
                # Work with unique targets list
                t = list(dict.fromkeys(c.strip().upper() for c in target_currencies if c))

                cross_updated = 0
                for x in range(len(t)):
                    for y in range(x + 1, len(t)):
                        a, b = t[x], t[y]
                        try:
                            cross_updated += cross_pair_with_usd(today_str, a, b, usd_rates_for_cross)
                        except Exception as e:
                            fail_count += 1
                            frappe.log_error(
                                title="Exchange Rate Sync: Cross upsert error",
                                message=f"A={a} B={b}\nError={e}"
                            )

                frappe.db.commit()
                results.append(f"Cross conversion: updated {cross_updated} forward pairs among target currencies.")
    except Exception as e:
        fail_count += 1
        frappe.log_error("Exchange Rate Sync", f"Cross conversion block failed: {e}")
        results.append("Cross conversion failed due to an internal error (check logs).")

    if fail_count and not success_count:
        return "Exchange rate sync failed for all bases:\n" + "\n".join(results)
    elif fail_count:
        return f"Exchange rate sync completed with issues ({success_count} succeeded, {fail_count} failed):\n" + "\n".join(results)
    else:
        return "Exchange rate sync completed successfully."

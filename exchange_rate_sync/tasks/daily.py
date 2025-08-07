
import requests
import frappe
from frappe.utils import today
import os
from dotenv import load_dotenv
import os
import time

# Load variables from .env file
load_dotenv()


def get_currency_exchange():
    URL = "https://api.exchangerate.host/live"
    API_KEY = os.getenv("API_KEY_EXCHANGERATEHOST")
    # Get enabled currencies (excluding base)
    enabled_currencies = frappe.get_all(
        "Currency",
        filters={"enabled": 1},
        pluck="name"
    )
    if not enabled_currencies:
        frappe.log_error("No enabled currencies found", "Exchange Rate Sync")
        return
    
    doc = frappe.get_doc("Exchange Rate Config", "Exchange Rate Config")

    # Determine base currencies to process       
    base_currencies = [row.currency for row in doc.base_currency_list]
    if not base_currencies:
        frappe.log_error("No base currencies configured", "Exchange Rate Sync")
        return

    for base_currency in base_currencies:
        target_currencies = [c for c in enabled_currencies if c != base_currency]
        if not target_currencies:
            frappe.log_error(f"No target currencies for base {base_currency}", "Exchange Rate Sync")
            continue

        # Prepare API params
        params = {
            "access_key": API_KEY,
            "source": base_currency,
            "currencies": ",".join(target_currencies)
        }


        response = requests.get(URL, params=params)
        data = response.json()

        if not data.get("success"):
            frappe.log_error(f"API error for {base_currency}: {response.text}", "Exchange Rate Sync")
            continue

        quotes = data.get("quotes", {})
        for pair, rate in quotes.items():
            if not pair.startswith(base_currency) or rate == 0:
                continue

            to_currency = pair.replace(base_currency, "")

            # Update or insert BASE → OTHER
            doc1 = frappe.db.get_value("Currency Exchange", {
                "date": today(),
                "from_currency": base_currency,
                "to_currency": to_currency
            }, "name")
            if doc1:
                frappe.db.set_value("Currency Exchange", doc1, "exchange_rate", rate)
                frappe.db.commit()

            else:
                new_doc1 = frappe.get_doc({
                    "doctype": "Currency Exchange",
                    "date": today(),
                    "from_currency": base_currency,
                    "to_currency": to_currency,
                    "exchange_rate": rate
                })
                new_doc1.insert(ignore_permissions=True)
                frappe.db.commit()

            # Update or insert OTHER → BASE
            reverse_doc = frappe.db.get_value("Currency Exchange", {
                "date": today(),
                "from_currency": to_currency,
                "to_currency": base_currency
            }, "name")

            reverse_rate = round(1 / rate, 6)
            if reverse_doc:
                frappe.db.set_value("Currency Exchange", reverse_doc, "exchange_rate", reverse_rate)
                frappe.db.commit()

                print(reverse_doc)
            else:
                new_doc2 = frappe.get_doc({
                    "doctype": "Currency Exchange",
                    "date": today(),
                    "from_currency": to_currency,
                    "to_currency": base_currency,
                    "exchange_rate": reverse_rate
                })
                new_doc2.insert(ignore_permissions=True)
                frappe.db.commit()
        time.sleep(1)

    return True

# The following block of code is for use with OpenExchangeRates API, which has limited features for free users

# def get_currency_exchange():
#     import time

#     URL = "https://openexchangerates.org/api/latest.json"
#     API_KEY = os.getenv("API_KEY_OPENEXCHANGERATES")

#     if not API_KEY:
#         frappe.log_error("Missing API key for openexchangerates.org", "Exchange Rate Sync")
#         return

#     # Get all enabled currencies
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
#             continue

#         # API call
#         params = {
#             "app_id": API_KEY,
#             "base": base_currency,  # Only works for free tier if USD 
#             "symbols": ",".join(target_currencies)
#         }

#         response = requests.get(URL, params=params)
#         if response.status_code != 200:
#             frappe.log_error(f"API failed for {base_currency}", response.text)
#             return False

#         data = response.json()
#         rates = data.get("rates", {})

#         for to_currency, rate in rates.items():
#             if not rate or rate == 0:
#                 continue

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
#                 frappe.get_doc({
#                     "doctype": "Currency Exchange",
#                     "date": today(),
#                     "from_currency": base_currency,
#                     "to_currency": to_currency,
#                     "exchange_rate": rate
#                 }).insert(ignore_permissions=True)
#                 frappe.db.commit()

#             # Update or insert OTHER → BASE
#             reverse_rate = round(1 / rate, 6)
#             reverse_doc = frappe.db.get_value("Currency Exchange", {
#                 "date": today(),
#                 "from_currency": to_currency,
#                 "to_currency": base_currency
#             }, "name")

#             if reverse_doc:
#                 frappe.db.set_value("Currency Exchange", reverse_doc, "exchange_rate", reverse_rate)
#                 frappe.db.commit()
#             else:
#                 frappe.get_doc({
#                     "doctype": "Currency Exchange",
#                     "date": today(),
#                     "from_currency": to_currency,
#                     "to_currency": base_currency,
#                     "exchange_rate": reverse_rate
#                 }).insert(ignore_permissions=True)
#                 frappe.db.commit()
#     return True



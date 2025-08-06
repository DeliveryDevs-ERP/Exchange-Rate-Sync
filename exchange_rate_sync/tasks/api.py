import requests
import frappe
from frappe.utils import today

# API_KEY = "799a708bb15c3d595f05e498483185ca"
# BASE_CURRENCY = frappe.db.get_single_value('Global Defaults', 'default_currency')
# URL = "https://api.exchangerate.host/live"

# def get_daily_currency_exchange():
#     # Get all enabled currencies except the base currency
#     enabled_currencies = frappe.get_all(
#         "Currency",
#         filters={"enabled": 1},
#         pluck="name"
#     )

#     target_currencies = [cur for cur in enabled_currencies if cur != BASE_CURRENCY]
#     if not target_currencies:
#         frappe.log_error("No enabled target currencies found", "Exchange Rate Sync")
#         return

#     # Prepare API params
#     params = {
#         "access_key": API_KEY,
#         "source": BASE_CURRENCY,
#         "currencies": ",".join(target_currencies)
#     }

#     response = requests.get(URL, params=params)

#     if response.status_code != 200:
#         frappe.log_error("Currency API failed", response.text)
#         return

#     data = response.json()
#     quotes = data.get("quotes", {})

#     for pair, rate in quotes.items():
#         if not pair.startswith(BASE_CURRENCY):
#             continue

#         other_currency = pair.replace(BASE_CURRENCY, "")
#         if not other_currency or rate == 0:
#             continue

#         # Insert BASE → OTHER
#         doc1 = frappe.new_doc("Currency Exchange")
#         doc1.date = today()
#         doc1.from_currency = BASE_CURRENCY
#         doc1.to_currency = other_currency
#         doc1.exchange_rate = rate
#         doc1.insert(ignore_permissions=True)

#         # Insert OTHER → BASE
#         doc2 = frappe.new_doc("Currency Exchange")
#         doc2.date = today()
#         doc2.from_currency = other_currency
#         doc2.to_currency = BASE_CURRENCY
#         doc2.exchange_rate = 1 / rate
#         doc2.insert(ignore_permissions=True)


# def delete_currency_exchange():
#     try:
#         frappe.db.delete("Currency Exchange")  # Replace with your Doctype
#         frappe.db.commit()
#         frappe.logger().info("Currency Exchange records deleted successfully.")
#     except Exception as e:
#         frappe.log_error(frappe.get_traceback(), "Monthly Currency Exchange Deletion Failed")




API_KEY = "e6f2d248b1754c01b3848038255d1b14"
BASE_CURRENCY = "USD"  # Fixed for openexchangerates.org API
URL = "https://openexchangerates.org/api/latest.json"

def get_daily_currency_exchange():
    # Get all enabled currencies except USD
    enabled_currencies = frappe.get_all(
        "Currency",
        filters={"enabled": 1},
        pluck="name"
    )

    target_currencies = [cur for cur in enabled_currencies if cur != BASE_CURRENCY]
    if not target_currencies:
        frappe.log_error("No enabled target currencies found", "Exchange Rate Sync (OXR)")
        return

    # Prepare params
    params = {
        "app_id": API_KEY,
        "symbols": ",".join(target_currencies)
    }

    response = requests.get(URL, params=params)
    if response.status_code != 200:
        frappe.log_error("OXR API failed", response.text)
        return

    data = response.json()
    rates = data.get("rates", {})

    for to_currency, rate in rates.items():
        if not rate or rate == 0:
            continue

        # Insert USD → to_currency
        doc1 = frappe.new_doc("Currency Exchange")
        doc1.date = today()
        doc1.from_currency = BASE_CURRENCY
        doc1.to_currency = to_currency
        doc1.exchange_rate = rate
        doc1.insert(ignore_permissions=True)

        # Insert to_currency → USD
        doc2 = frappe.new_doc("Currency Exchange")
        doc2.date = today()
        doc2.from_currency = to_currency
        doc2.to_currency = BASE_CURRENCY
        doc2.exchange_rate = 1 / rate
        doc2.insert(ignore_permissions=True)

import requests
import frappe
from frappe.utils import today
import os



def get_currency_exchange():
    URL = "https://api.exchangerate.host/live"  # This provides only 100 calls per month for the free tier
    API_KEY="YOUR_API_KEY"

    base_currency = frappe.db.get_single_value('Exchange Rate Config', 'base_currency') # from single doctype
   
    enabled_currencies = frappe.get_all(
        "Currency",
        filters={"enabled": 1},
        pluck="name"
    )

    target_currencies = [cur for cur in enabled_currencies if cur != base_currency]
    if not target_currencies:
        frappe.log_error("No enabled target currencies found", "Exchange Rate Sync")
        return False

    # Prepare params
    params = {
        "access_key": API_KEY,
        "source": base_currency,
        "currencies": ",".join(target_currencies)
    }

    response = requests.get(URL, params=params)
    data = response.json()

    if data.get("success") is False:
        frappe.log_error("API request failed", response.text)
        return False
    # delete today's previously saved exchange rates (if existing) in order to update the records
    if frappe.db.exists("Currency Exchange", {"date": today(), "from_currency": base_currency}):
        frappe.db.delete(
            "Currency Exchange",
            {
                "date": today(),
                "from_currency": base_currency
            }
        )
        frappe.db.delete(
            "Currency Exchange",
            {
                "date": today(),
                "to_currency": base_currency
            }
        )
        frappe.db.commit()
        frappe.logger().info(f"Deleted recent Currency Exchange records for {base_currency} on {today()}.")
    # get new exchange rates
    quotes = data.get("quotes", {})
    print(quotes)
    for pair, rate in quotes.items():
        if not pair.startswith(base_currency):
            frappe.log_error("API GET request not successful for base currency", "Exchange Rate Sync")
            return False

        to_currency = pair.replace(base_currency, "")
        if not to_currency or rate == 0:
            frappe.log_error("Exchange rate 0 not possible. Check API data.", "Exchange Rate Sync")
            continue
        
        # save new exchange rates
#       Insert BASE → OTHER  
        doc1 = frappe.new_doc("Currency Exchange")
        doc1.date = today()
        doc1.from_currency = base_currency
        doc1.to_currency = to_currency
        doc1.exchange_rate = rate
        doc1.insert(ignore_permissions=True)

#       Insert OTHER → BASE
        doc2 = frappe.new_doc("Currency Exchange")
        doc2.date = today()
        doc2.from_currency = to_currency
        doc2.to_currency = base_currency
        doc2.exchange_rate = 1 / rate
        doc2.insert(ignore_permissions=True)
    return True


@frappe.whitelist()
def get_currency_exchange_from_ui():
    return get_currency_exchange()

# # The following block of code is for use with OpenExchangeRates API, which has limited features for free users

# URL = "https://openexchangerates.org/api/latest.json" # This provides 1000 calls per month for free but only for base USD
# API_KEY="YOUR_API_KEY"
# def get_currency_exchange():
#     base_currency = frappe.db.get_single_value('Exchange Rate Config', 'base_currency') # If base has been set to USD from UI
#     # base_currency = "USD"  # Fixed for openexchangerates.org API

   
#     enabled_currencies = frappe.get_all(
#         "Currency",
#         filters={"enabled": 1},
#         pluck="name"
#     )

#     target_currencies = [cur for cur in enabled_currencies if cur != base_currency]
#     if not target_currencies:
#         frappe.log_error("No enabled target currencies found", "Exchange Rate Sync")
#         frappe.throw("No foreign currencies found. Please set/enable target currencies")

#     # Prepare params
#     params = {
#         "app_id": API_KEY,
#         "base": base_currency,
#         "symbols": ",".join(target_currencies)
#     }

#     response = requests.get(URL, params=params)
#     data = response.json()

#     if response.status_code != 200:
#         frappe.log_error("API request failed", response.text)
#         return False
    
#     if frappe.db.exists("Currency Exchange", {"date": today(), "from_currency": base_currency}):
#         frappe.db.delete(
#             "Currency Exchange",
#             {
#                 "date": today(),
#                 "from_currency": base_currency
#             }
#         )
#         frappe.db.delete(
#             "Currency Exchange",
#             {
#                 "date": today(),
#                 "to_currency": base_currency
#             }
#         )
#         frappe.db.commit()
#         frappe.logger().info(f"Deleted recent Currency Exchange records for {base_currency} on {today()}.")
 
#     rates = data.get("rates", {})

#     for to_currency, rate in rates.items():
#         if not rate or rate == 0:
#             continue

#         # Insert BASE → OTHER
#         doc1 = frappe.new_doc("Currency Exchange")
#         doc1.date = today()
#         doc1.from_currency = base_currency
#         doc1.to_currency = to_currency
#         doc1.exchange_rate = rate
#         doc1.insert(ignore_permissions=True)

#         # Insert OTHER → BASE
#         doc2 = frappe.new_doc("Currency Exchange")
#         doc2.date = today()
#         doc2.from_currency = to_currency
#         doc2.to_currency = base_currency
#         doc2.exchange_rate = 1 / rate
#         doc2.insert(ignore_permissions=True)
#     return True



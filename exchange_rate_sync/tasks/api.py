
import frappe
import requests
from .daily import get_currency_exchange



ERROR_EXPLANATIONS = {
    "invalid_app_id": "Invalid App ID provided. Please check your API Key.",
    "missing_app_id": "No App ID provided. Please provide an API Key.",
    "not_allowed": "This App ID does not have access to the requested feature.",
    "access_restricted": "Access restricted due to overuse or account limits.",
    "invalid_base": "The requested base currency is not supported.",
    "not_found": "The requested API route or resource does not exist."
}

@frappe.whitelist()
def test_connection():
    doc = frappe.get_doc("Exchange Rate Config", "Exchange Rate Config")

    url = f"https://openexchangerates.org/api/usage.json?app_id={doc.api_key}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json().get("data", {})

        doc.connection_success = 1
        doc.quota = data["plan"].get("quota", "N/A")
        doc.plan = data["plan"].get("name", "N/A")
        doc.api_status = data.get("status", "active")

        # Set currency option and table permissions
        if data["plan"]["features"].get("base", False):
            doc.from_currency_option = "All Currencies"
        else:
            doc.from_currency_option = "USD Only"

        # Show usage info button
        doc.save()

        return {
            "status": "success",
            "message": "Connection successful. Fields have been updated.",
            "base_enabled": data["plan"]["features"].get("base", False)
        }
    else:
        # Failed connection
        error_json = response.json()
        error_code = error_json.get("message", "Unknown Error")
        explanation = ERROR_EXPLANATIONS.get(error_code, "Unknown error. Please try again or contact support.")

        doc.connection_success = 0
        doc.quota = "N/A"
        doc.plan = "N/A"
        doc.api_status = f"{explanation}"
        doc.from_currency_option = "N/A"
        doc.set_onload("api_usage_info_visible", False)
        doc.set_onload("from_currency_read_only", True)
        doc.set_onload("to_currency_read_only", True)
        # Hide usage info button
        doc.save()

        return {
        "status": "failure",
        "error_code": error_code,
        "message": f"Connection failed: {error_code} — {explanation}"
        }


@frappe.whitelist()
def get_api_usage_info(api_key):
    """Fetch live API usage details from the selected provider"""
    url = "https://openexchangerates.org/api/usage.json"
    
    try:
        resp = requests.get(url, params={"app_id": api_key}, timeout=8)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException as e:
        frappe.throw(f"Failed to fetch usage info: {str(e)}")

    if data.get("status") != 200:
        desc = data.get("description") or data.get("message") or "Unknown error."
        frappe.throw(f"Failed to fetch usage info: {desc}")

    usage = data.get("data", {}).get("usage", {})
    return usage

@frappe.whitelist()
def get_currency_exchange_ui():
    return get_currency_exchange()



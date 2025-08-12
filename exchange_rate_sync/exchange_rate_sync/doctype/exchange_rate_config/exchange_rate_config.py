# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import requests



ERROR_EXPLANATIONS = {
    "invalid_app_id": "Invalid App ID provided. Please check your API Key.",
    "missing_app_id": "No App ID provided. Please provide an API Key.",
    "not_allowed": "This App ID does not have access to the requested feature.",
    "access_restricted": "Access restricted due to overuse or account limits.",
    "invalid_base": "The requested base currency is not supported.",
    "not_found": "The requested API route or resource does not exist."
}


class ExchangeRateConfig(Document):

    def validate(self):
        # Validate API key and auto-set from_currency_option based on plan
        if self.api_key:
            test_connection(self)

        # Collect current values
        from_vals = [r.from_currency for r in self.from_currency_table]
        to_vals   = [r.to_currency for r in self.to_currency_table]

        # Decide final from-currency list based on option
        option = (self.from_currency_option or "").strip()

        if option == "USD Only":
            final_from = ["USD"]                       # exactly one row, USD
        elif option == "All Currencies":
            final_from = normalize_list(from_vals)     # keep values, remove duplicates, uppercase
        else:
            final_from = []                            # empty in all other cases

        # Decide final to-currency list based on API status
        if (self.api_status or "").strip().lower() == "active":
            final_to = normalize_list(to_vals)         # keep values, remove duplicates, uppercase
        else:
            final_to = []                              # empty if not active

        # Write back
        write_child_table(self, "from_currency_table", final_from, "from_currency")
        write_child_table(self, "to_currency_table", final_to, "to_currency")

        frappe.db.commit()


def normalize_list(lst):
    """
    - Remove empties
    - Deduplicate (case-insensitive)
    - Normalize to uppercase (ISO currency style)
    - Preserve first-seen order
    """
    if not lst:
        return []

    seen = set()
    cleaned = []
    for s in lst:
        if not isinstance(s, str):
            continue
        v = s.strip().upper()
        if not v:
            continue
        if v not in seen:
            seen.add(v)
            cleaned.append(v)
    return cleaned


def write_child_table(doc: Document, table_attr: str, values: list[str], currency_field: str):
    """
    Overwrites the child table with the given values (assumed already normalized if needed).
    No empty placeholder rows will be created.
    """
    doc.set(table_attr, [])  # Clear
    for v in values:
        doc.append(table_attr, {currency_field: v})


def test_connection(doc):
    if doc.enabled == 0:
        return

    url = f"https://openexchangerates.org/api/usage.json?app_id={doc.api_key}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json().get("data", {})

        doc.connection_success = 1
        doc.quota = data["plan"].get("quota", "N/A")
        doc.plan = data["plan"].get("name", "N/A")
        doc.api_status = data.get("status", "active")

        # Set currency option from plan features
        if data["plan"]["features"].get("base", False):
            doc.from_currency_option = "All Currencies"
        else:
            doc.from_currency_option = "USD Only"

        frappe.db.commit()
        frappe.msgprint("Connection successful. Fields have been updated.")


    else:
        error_json = response.json()
        error_code = error_json.get("message", "Unknown Error")
        explanation = ERROR_EXPLANATIONS.get(error_code, "Unknown error. Please try again or contact support.")

        doc.connection_success = 0
        doc.quota = "N/A"
        doc.plan = "N/A"
        doc.api_status = f"{explanation}"
        doc.from_currency_option = "N/A"
        frappe.db.commit()
        frappe.msgprint(f"Connection failed: {error_code} — {explanation}")

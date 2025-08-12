# Copyright (c) 2025, DeliveryDevs  and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ExchangeRateConfig(Document):
    def before_insert(self):
        if not self.api_provider:
            self.api_provider = "openexchangerates.org"
        if not self.from_currency_table:
            self.append("from_currency_table", {
                "from_currency": "USD"  
            })
        if not self.to_currency_table:
            self.append("to_currency_table", {
                "from_currency": ""  
            })
        self.from_currency_option = "N/A"
        self.quota = "N/A"
        self.plan = "N/A"
        self.api_status = "Status not available. Please test connection first."
        frappe.db.commit()
    
    def validate(self):
        # Read current values from both child tables
        from_vals = [r.from_currency for r in self.from_currency_table]
        to_vals   = [r.to_currency for r in self.to_currency_table]
        # Normalize and write back
        write_child_table(self, "from_currency_table", from_vals, "from_currency")
        write_child_table(self, "to_currency_table", to_vals, "to_currency")
        frappe.db.commit()


        


def normalize_list(lst):
    """
    If the list is empty or has only empty strings -> return ['']
    Otherwise -> return the list with all empty strings removed and no duplicates (case-insensitive)
    """
    seen_lower = set()
    cleaned = []

    for s in lst:
        if not isinstance(s, str):
            continue
        val = s.strip()
        if val and val.lower() not in seen_lower:
            seen_lower.add(val.lower())
            cleaned.append(val)

    if not cleaned:
        return [""]
    else:
        return cleaned


def write_child_table(doc: Document, table_attr: str, values: list[str], currency_field: str):
    """
    Overwrites the child table with the normalized values:
      - If normalized == [''] -> creates exactly one empty row
      - Else -> one row per value, no empty rows
    """
    normalized = normalize_list(values)

    # Clear existing rows
    doc.set(table_attr, [])

    if normalized == [""]:
        # One empty row
        doc.append(table_attr, {currency_field: ""})
    else:
        for v in normalized:
            doc.append(table_attr, {currency_field: v})


import frappe
from frappe.utils import nowdate, add_days

def delete_currency_exchange_monthly():
    if frappe.get_doc("Exchange Rate Config", "Exchange Rate Config").enabled == 0:
        frappe.log_error("Exchange Rate Sync", "sync not enabled")
        return "Exchange rate sync is disabled in Exchange Rate Config"

    try:
        # Calculate the date before yesterday
        yesterday = add_days(nowdate(), -1)

        # Delete all records with a date less than yesterday (i.e., before yesterday)
        frappe.db.delete(
            "Currency Exchange",
            filters={
                "date": ("<", yesterday)
            }
        )
        frappe.db.commit()
        frappe.logger().info("Deleted Currency Exchange records older than yesterday.")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Exchange Rate Cleanup Failed")

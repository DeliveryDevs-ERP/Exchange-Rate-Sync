// Copyright (c) 2025, DeliveryDevs  and contributors
// For license information, please see license.txt


frappe.ui.form.on('Exchange Rate Config', {
    update_exchange_rates: function(frm) {
        frm.__triggered_from_button = true; // flag to avoid duplicate error message from after_save event
        function call_sync_function() {
            frappe.call({
                method: "exchange_rate_sync.tasks.daily.get_currency_exchange_from_ui",
                callback: function(r) {
                    if (r.message === false) {
                        frappe.msgprint({
                            title: __('Error'),
                            message: __('Exchange rates could not be updated. Check Exchange Rate API settings/permissions.'),
                            indicator: 'red'
                        });
                    } else {
                        frappe.msgprint("Exchange rates updated successfully.");
                    }
                    // Reset flag after operation
                    frm.__triggered_from_button = false;
                }
            });
        }
        // saves the doctype and syncs the exchange rates according to new base currency
        if (frm.is_dirty()) {
            frm.save()
            .then(() => {
                call_sync_function();
            });
        } else {
            call_sync_function();
        }
    },

    // updates the exchange rates for today after a new base currency has been saved in the doctype
    after_save: function(frm) {
        // To ensure that frm.save() hasn't already been triggered
        if (frm.__triggered_from_button) {
            return;
        }
        frappe.call({
            method: "exchange_rate_sync.tasks.daily.get_currency_exchange_from_ui",
            callback: function(r) {
                if (r.message === false) {
                    frappe.msgprint({
                        title: __('Error'),
                            message: __('Exchange rates could not be updated. Check Exchange Rate API settings/permissions.'),
                        indicator: 'red'
                    });
                } else {
                    frappe.msgprint("Exchange rates added successfully.");
                }
            }
        });
    }
});

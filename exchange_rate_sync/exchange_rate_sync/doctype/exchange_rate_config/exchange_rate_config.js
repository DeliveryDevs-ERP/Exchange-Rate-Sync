// // Copyright (c) 2025, DeliveryDevs  and contributors
// // For license information, please see license.txt


frappe.ui.form.on('Exchange Rate Config', {
    onload: function(frm) {
        Promise.all([
            frappe.call('exchange_rate_sync.tasks.api.get_base_currency_list'),
            frappe.call('exchange_rate_sync.tasks.api.get_all_currency_list')
        ])
        .then(([baseRes, allRes]) => {
            let base = Array.isArray(baseRes.message) ? baseRes.message : [];
            let all = Array.isArray(allRes.message) ? allRes.message : [];
            console.log(base.length)
            // Find currencies not in base
            let difference = all.filter(currency => !base.includes(currency));
            frm.set_df_property('select_currency_to_add', 'options', difference);
            frm.refresh_field('select_currency_to_add');


            base = base.filter(Boolean)
            if (base.length > 0) {
            base.unshift("All");
            frm.set_df_property('select_base_currency', 'options', base);
            frm.refresh_field('select_base_currency');
            frm.set_value('select_base_currency', 'All');
            frm.set_df_property('select_currency_to_remove', 'options', base);
            frm.refresh_field('select_currency_to_remove');



            } else {
            frm.set_df_property('select_base_currency', 'options', []);
            frm.refresh_field('select_base_currency');
            frm.set_df_property('select_currency_to_remove', 'options', []);
            frm.refresh_field('select_currency_to_remove');

}
        });
    },


    add: function(frm) {
        let currency = frm.doc.select_currency_to_add;

        if (!currency) {
            frappe.msgprint("Please select a currency to add.");
            return;
        }

        frappe.call({
            method: 'exchange_rate_sync.tasks.api.add_base_currency',
            args: {
                curr: currency
            },
        callback: function(r) {
                if (r.message === false) {
                        frappe.msgprint({
                            title: __('Error'),
                            message: __('Some exchange rates could not be updated. Check Exchange Rate API settings/permissions.'),
                            indicator: 'red'
                        });
                    } else {
                        frappe.show_alert(`Exchange rates for ${currency} added successfully`);
                        frm.reload_doc();   
                                                
                        }

                }
            }
        );
    },
    remove: function(frm) {
            let currency = frm.doc.select_currency_to_remove;

            if (!currency) {
                frappe.msgprint(__('Please select a currency to remove.'));
                return;
            }

            frappe.call({
                method: 'exchange_rate_sync.tasks.api.remove_base_currency',
                args: {
                    curr: currency
                },
                callback: function() {
                       frappe.show_alert(`${currency} removed successfully`);
                         frm.reload_doc();  
                }
            });
        },

    
    update: function(frm) {
        let currency = frm.doc.select_base_currency;

        if (!currency) {
            frappe.msgprint("Please select a currency to update.");
            return;
        }

        frappe.call({
            method: 'exchange_rate_sync.tasks.api.update_exchange_rates',
            args: {
                curr: currency
            },
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

                }
            }
        );
    },
    })

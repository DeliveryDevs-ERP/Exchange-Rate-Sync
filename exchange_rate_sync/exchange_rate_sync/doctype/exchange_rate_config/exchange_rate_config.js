// // // // Copyright (c) 2025, DeliveryDevs  and contributors
// // // // For license information, please see license.txt



frappe.ui.form.on('Exchange Rate Config', {

   onload: function(frm) {
    persist_ui_fields(frm);
  },

    refresh: function(frm) {
        persist_ui_fields(frm);
        toggle_fields_visibility(frm);
        frm.add_custom_button(__('Test Connection'), function() {
            if (!frm.doc.enabled) {
                frappe.msgprint(__('Please enable first.'));
                return;
            }   
            // test_connection()
            // If the form is dirty, save it first
            if (frm.is_dirty()) {
                frm.save().then(() => test_connection());
            } else {
                test_connection();
            }
        });

    },

    // Trigger this function whenever the 'enable' checkbox changes
        enabled: function(frm) {
        // Call the function to control visibility based on 'enable' field
        toggle_fields_visibility(frm);
    },

    api_usage_info: async function(frm) {
    const is_valid = frm.doc.enabled && frm.doc.connection_success === 1;

    if (!is_valid || frm.is_dirty()) {
      frappe.msgprint(__('Please test the connection first.'));
      return;
    }

    try {
      const { message: usage = {} } = await frappe.call({
        method: "exchange_rate_sync.tasks.api.get_api_usage_info",
        args: { api_key: frm.doc.api_key },
        freeze: true,
        freeze_message: __("Fetching API usage..."),
      });

      frappe.msgprint({
        title: __("API Usage Information"),
        message: `
          <div style="padding:8px 0;">
            <strong>Requests:</strong> ${usage.requests ?? 0}<br>
            <strong>Requests Quota:</strong> ${usage.requests_quota ?? 0}<br>
            <strong>Requests Remaining:</strong> ${usage.requests_remaining ?? 0}<br>
            <strong>Days Elapsed:</strong> ${usage.days_elapsed ?? 0}<br>
            <strong>Days Remaining:</strong> ${usage.days_remaining ?? 0}<br>
            <strong>Daily Average:</strong> ${usage.daily_average ?? 0}
          </div>
        `,
        indicator: "blue",
      });

    } catch (error) {
      frappe.msgprint({
        title: __("Error"),
        message: __("Invalid API Key or failed to fetch usage info."),
        indicator: "red"
      });
      await frm.reload_doc();
    }
  }, 
update_exchange_rates: function(frm) {
    if (frm.is_dirty()) {
      frappe.msgprint("Please save the document first.")
    } else {
        call_update_exchange_rates(frm);
    }
}
});

// Function to toggle the visibility of fields
function toggle_fields_visibility(frm) {
    // Unhide the fields when 'enable' is checked
    persist_ui_fields(frm)


    const isEnabled = !!frm.doc.enabled;
    ['api_status', 'plan', 'quota', 'from_currency_option']
    .forEach(f => frm.set_df_property(f, "hidden", isEnabled ? 0 : 1));
    frm.set_df_property("api_key", "read_only", isEnabled ? 0 : 1);
    frm.set_df_property("api_key", "reqd", isEnabled ? 1 : 0);
 
    // Refresh the form after toggling visibility
    frm.refresh_fields();
}


function test_connection() {
    frappe.call({
        method: 'exchange_rate_sync.tasks.api.test_connection',
        callback: function(r) {
            if (!r.exc && r.message) {
                const result = r.message;

                frappe.msgprint(result.message);

                // Reload doc values
                cur_frm.reload_doc();

            }
        }
    });
}

function persist_ui_fields(frm) {
    const ok = cint(frm.doc.enabled) === 1 &&
    cint(frm.doc.connection_success) === 1;


  frm.set_df_property('api_usage_info', 'hidden', ok ? 0 : 1);
  frm.set_df_property("to_currency_table", "read_only", ok ? 0 : 1);
  // frm.set_df_property("update_exchange_rates", "hidden", ok ? 0 : 1);

  if (ok && frm.doc.from_currency_option === "USD Only") {
  frm.set_df_property("from_currency_table", "read_only", 1);
  } else if (ok && frm.doc.from_currency_option === "All Currencies") {
  frm.set_df_property("from_currency_table", "read_only", 0);
  }
}

function call_update_exchange_rates(frm) {
    frappe.call({
        method: "exchange_rate_sync.tasks.api.get_currency_exchange_ui",
        freeze: true,
        freeze_message: __("Updating exchange rates..."),
        callback: function(r) {
            if (r.message) {
                frappe.msgprint(r.message);
                frm.reload_doc();
            }
        }
    });
}
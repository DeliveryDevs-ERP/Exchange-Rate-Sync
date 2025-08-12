// // // // Copyright (c) 2025, DeliveryDevs  and contributors
// // // // For license information, please see license.txt



frappe.ui.form.on('Exchange Rate Config', {

   onload: function(frm) {
    persist_ui_fields(frm);
      if  (!frm.doc.api_provider){
        frm.set_value("api_provider", "https://openexchangerates.org/");
      }
  },

    refresh: function(frm) {
        persist_ui_fields(frm);
        toggle_fields_visibility(frm);
    frm.add_custom_button(__('Test Connection'), async () => {
      await test_connection_button_action(frm);
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
    ['api_status', 'plan', 'quota', 'from_currency_option', 'from_currency_table', 'to_currency_table']
    .forEach(f => frm.set_df_property(f, "hidden", isEnabled ? 0 : 1));
    frm.set_df_property("api_key", "read_only", isEnabled ? 0 : 1);
    frm.set_df_property("api_key", "reqd", isEnabled ? 1 : 0);
 
    // Refresh the form after toggling visibility
    frm.refresh_fields();
}




function persist_ui_fields(frm) {
    const ok = cint(frm.doc.enabled) === 1 &&
    cint(frm.doc.connection_success) === 1;


  frm.set_df_property('api_usage_info', 'hidden', ok ? 0 : 1);
  frm.set_df_property("to_currency_table", "read_only", ok ? 0 : 1);
  frm.set_df_property("update_exchange_rates", "hidden", ok ? 0 : 1);

if (ok && frm.doc.from_currency_option === "All Currencies") {
    // Editable only in this case
    frm.set_df_property("from_currency_table", "read_only", 0);
} else {
    // Read-only for USD Only or any other case
    frm.set_df_property("from_currency_table", "read_only", 1);
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

async function test_connection_button_action(frm) {
  // Require enabled
  if (!frm.doc.enabled) {
    frappe.msgprint(__('Please enable first.'));
    return;
  }

  // If the form is dirty → just save silently
  if (frm.is_dirty()) {
    await frm.save(); // no messages shown
    return;
  }

  // Require API key
  if (!frm.doc.api_key) {
    frappe.msgprint(__('Please enter an API Key first.'));
    return;
  }

  // Not dirty → call the server
  frappe.call({
    method: 'exchange_rate_sync.tasks.api.test_connection_ui',
    freeze: true,
    freeze_message: __('Testing connection...'),
    args: {},

    callback: (r) => {
      const res = r.message || {};
      if (res.status === 'success') {
        frappe.msgprint({
          title: __('Connection Successful'),
          message: __(
            `<b>Status:</b> ${res.status}<br>
             <b>Message:</b> ${res.message || ''}<br>
             <b>Base Enabled:</b> ${res.base_enabled ? 'Yes' : 'No'}`
          ),
          indicator: 'green'
        });
      } else {
        frappe.msgprint({
          title: __('Connection Failed'),
          message: __(
            `<b>Status:</b> ${res.status}<br>
             <b>Error Code:</b> ${res.error_code || 'N/A'}<br>
             <b>Message:</b> ${res.message || ''}`
          ),
          indicator: 'red'
        });
      }
      frm.reload_doc();
    },

    error: () => {
      frappe.msgprint({
        title: __('Error'),
        message: __('Server error while testing connection.'),
        indicator: 'red'
      });
    }
  });
}
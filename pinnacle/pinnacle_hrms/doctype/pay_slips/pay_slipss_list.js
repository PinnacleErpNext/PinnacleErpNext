frappe.listview_settings["Pay Slips"] = {
  onload: function (listview) {
    debugger;

    listview.page.add_action_item(__("Email Pay Slips"), function () {
      let selected_pay_slips = listview.get_checked_items();
      frappe.call({
        method: "mygstcafe.api.email_pay_slip",
        args: {
          pay_slips: selected_pay_slips,
        },
        callback: function (res) {
          frappe.msgprint("Pay slip emailed successfully!");
        },
        error: function (r) {
          frappe.msgprint(r.message);
        },
      });
    });
  },
};

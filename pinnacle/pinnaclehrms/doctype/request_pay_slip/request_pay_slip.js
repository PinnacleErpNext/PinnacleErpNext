// Copyright (c) 2024, mygstcafe and contributors
// For license information, please see license.txt

frappe.ui.form.on("Request Pay Slip", {
    refresh: function (frm) {
      if (!frm.is_new() && frm.doc.status == "Requested") {
        frm.add_custom_button(__("Approve"), function () {
          const monthName = frm.doc.month;
          const months = {
            January: 1,
            February: 2,
            March: 3,
            April: 4,
            May: 5,
            June: 6,
            July: 7,
            August: 8,
            September: 9,
            October: 10,
            November: 11,
            December: 12,
          };
  
          let monthNum = months[monthName];
          frappe.call({
            method: "mygstcafe.api.approve_pay_slip_req",
            args: {
              employee: frm.doc.employee,
              year: frm.doc.year,
              month: monthNum,
            },
            callback: function () {
              frm.reload_doc();
            },
          });
        });
      }
    },
  });
  
frappe.pages["set-defaults"].on_page_load = function (wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: "",
        single_column: true,
    });

    $(`
        <div style="display: flex; height: 200px; justify-content: center; align-items: center;">
          <div id="company-selection-container" style="display: flex; flex-direction: column; gap:10px; align-items: center;">
            <label for="company-select" style="font-weight: bold;">Select your Company</label>
            <select id="company-select" style="padding: 5px; border: 1px solid #d1d8dd; border-radius: 4px;">
              <option value="Select">Select</option>
            </select>
            <label for="select-fiscal_year" style="font-weight: bold;">Select Fiscal Year</label>
            <select id="select-fiscal_year" style="padding: 5px; border: 1px solid #d1d8dd; border-radius: 4px;">
              <option value="Select">Select</option>
            </select>
            <button id="set_defaults" class="btn btn-primary" style="padding: 5px 10px;" disabled>Proceed</button>
          </div>
        </div>
    `).appendTo(page.main);

    function setDefaults() {
        var selectedCompany = $("#company-select").val();
        var selectedFiscalYear = $("#select-fiscal_year").val();

        if (selectedCompany === "Select" || selectedFiscalYear === "Select") {
            frappe.msgprint({
                title: __("Invalid Selection"),
                message: __("Please select both a valid company and fiscal year."),
                indicator: "red",
            });
            return;
        }

        frappe.call({
            method: "pinnacleerpnext.api.set_default_settings",
            args: {
                data: JSON.stringify({
                    company_name: selectedCompany,
                    fiscal_year: selectedFiscalYear,
                    currUser: frappe.session.user_email,
                }),
            },
            callback: function (res) {
                if (res.message) {
                    if (res.message.error) {
                        frappe.msgprint({
                            title: __("Error"),
                            message: __(res.message.error),
                            indicator: "red",
                        });
                    } else {
                        let route = res.message.user === "Employee" ? "/app/employee-dashboard" : "/app/home";
                        frappe.set_route(route);
                    }
                }
            },
            error: function () {
                frappe.msgprint({
                    title: __("Error"),
                    message: __("Failed to set default settings."),
                    indicator: "red",
                });
            },
        });
    }

    $("#set_defaults").on("click", setDefaults);

    function toggleProceedButton() {
        var selectedCompany = $("#company-select").val();
        var selectedFiscalYear = $("#select-fiscal_year").val();
        $("#set_defaults").prop("disabled", selectedCompany === "Select" || selectedFiscalYear === "Select");
    }

    $("#company-select, #select-fiscal_year").on("change", toggleProceedButton);

    frappe.call({
        method: "pinnacleerpnext.api.get_default_company_and_list",
        callback: function (res) {
            if (res.message) {
                var data = res.message;
                var defaultCompany = data.default_company;
                var companies = data.companies;
                var defaultFiscalYear = data.default_fiscal_year;
                var fiscalYears = data.fiscal_years;

                var companySelect = $("#company-select");
                var fiscalYearSelect = $("#select-fiscal_year");

                companies.forEach(function (company) {
                    companySelect.append(
                        `<option value="${company.name}">${company.company_name}</option>`
                    );
                });

                fiscalYears.forEach(function (fiscalYear) {
                    fiscalYearSelect.append(
                        `<option value="${fiscalYear.name}">${fiscalYear.name}</option>`
                    );
                });

                if (defaultCompany) {
                    companySelect.val(defaultCompany);
                }
                if (defaultFiscalYear) {
                    fiscalYearSelect.val(defaultFiscalYear);
                }

                toggleProceedButton();
            }
        },
    });
};
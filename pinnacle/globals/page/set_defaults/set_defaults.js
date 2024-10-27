frappe.pages["set-defaults"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
	  parent: wrapper,
	  title: "",
	  single_column: true,
	});
	
	$(`
		<div style="display: flex; height: 200px; justify-content: center; align-items: center;">
		  <div id="company-selection-container" style="display: flex; flex-direction: column; gap:10px; align-items: center;">
			<label for="company" style="margin-right: 10px; font-weight: bold;">Select your Company</label>
			<select id="company-select" style="flex: 1; margin-right: 10px; padding: 5px; border: 1px solid #d1d8dd; border-radius: 4px;">
			  <option value="Select" id="company-options">Select</option>
			</select>
			<label for="company" style="margin-right: 10px; font-weight: bold;">Select Fiscal Year</label>
			<select id="select-fiscal_year" style="flex: 1; margin-right: 10px; padding: 5px; border: 1px solid #d1d8dd; border-radius: 4px;">
			  <option value="Select" id="fiscal-year-options">Select</option>
			</select>
			<button id="set_defaults" class="btn btn-primary" style="padding: 5px 10px;">Proceed</button>
		  </div>
		</div>
	  `).appendTo(page.main);
  
	// Function to set defaults
	function setDefaults() {
	  var selectedCompany = $("#company-select").val();
	  var selectedFiscalYear = $("#select-fiscal_year").val();
	  frappe.call({
		method: "pinnacle.api.set_default_settings",
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
			  if (res.message.user === "Employee") {
				frappe.set_route("/app/employee-dashboard");
				location.reload();
			  } else {
				frappe.set_route("/app/home");
				location.reload();
			  }
			}
		  }
		},
	  });
	}
  
	// Bind the click event to the change button
	$("#set_defaults").on("click", setDefaults);
  
	// Fetch default company and fiscal_year, companies and fiscal years
	frappe.call({
	  method: "pinnacle.api.get_default_company_and_list",
	  callback: function (res) {
		if (res.message) {
		  var data = res.message;
		  var defaultCompany = data.default_company;
		  var companies = data.companies;
		  var defaultFiscalYear = data.default_fiscal_year;
		  var fiscalYears = data.fiscal_years;
  
		  var companySelect = $("#company-select");
		  companies.forEach(function (company) {
			companySelect.append(
			  `<option value="${company.name}">${company.company_name}</option>`
			);
		  });
  
		  var selectFiscalYear = $("#select-fiscal_year");
		  fiscalYears.forEach(function (fiscalYear) {
			selectFiscalYear.append(
			  `<option value="${fiscalYear.name}">${fiscalYear.name}</option>`
			);
		  });
  
		  // If there is a default company, select it
		  if (defaultCompany) {
			companySelect.val(defaultCompany);
		  }
		  if (defaultFiscalYear) {
			selectFiscalYear.val(defaultFiscalYear);
		  }
		  $("#company-selection-container").show();
		}
	  },
	});
  };
  
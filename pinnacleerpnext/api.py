import frappe
import frappe.defaults
import json

# API to get default company and list
@frappe.whitelist(allow_guest=True)
def get_default_company_and_list():
    user = frappe.session.user
    
    default_company = frappe.db.get_value("DefaultValue", {"parent": user, "defkey": "company"}, "defvalue")
    default_fiscal_year = frappe.db.get_value("DefaultValue",{"parent": user, "defkey":"fiscal_year"},"defvalue")
    
    companies = frappe.get_all("Company", fields=["name", "company_name"])
    fiscal_years = frappe.get_all("Fiscal Year",fields=["name"])
    
    return {
        "default_company": default_company,
        "default_fiscal_year": default_fiscal_year,
        "companies": companies,
        "fiscal_years": fiscal_years
    }

# API to set default settings
@frappe.whitelist(allow_guest=True)
def set_default_settings(data):
    user = ""
    data = json.loads(data)  
    company_name = data.get('company_name')
    fiscal_year = data.get('fiscal_year')
    curr_user = data.get('currUser')
    user_roles = frappe.get_roles(curr_user) 
    if 'Employee' in user_roles:
        user = "Employee"
    if not company_name and not fiscal_year :
        return { "error": "Data Missing" }
    
    try:
        frappe.defaults.set_user_default("company", company_name)
        frappe.defaults.set_user_default("fiscal_year", fiscal_year)
        
        return { "message": "Defaults set successfully.", "user": user }
    except Exception as e:
        return { "error": str(e) }

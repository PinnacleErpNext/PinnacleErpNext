import frappe
import frappe.defaults
from frappe import _
import json
import base64
import os
import uuid
from frappe import sendmail
from collections import defaultdict
from frappe.core.doctype.communication.email import make
import frappe.utils
import frappe.utils.print_format
from pinnacle.pinnaclehrms.salary_calculator import createPaySlips, getEmpRecords, calculateMonthlySalary

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

@frappe.whitelist(allow_guest=True)
def get_item_defaults():
    user = frappe.session.user
    
    default_company = frappe.db.get_value("DefaultValue", {"parent": user, "defkey": "company"}, "defvalue")
    
    return default_company

# API to get pay slips in create pay slips
@frappe.whitelist(allow_guest=True)
def get_pay_slip_list(parent_docname,month,year,company=None, employee=None):
    baseQuery = """
                SELECT
                    name,
                    employee_name,
                    employee_id,
                    net_payble_amount 
                FROM
                    `tabPay Slips` 
                WHERE 
                    month_num = %s AND year = %s
                """
    filters = [month,year]
    if (company != ""):
        filters.append(company)
        baseQuery += "AND company = %s"
    if (employee != ""):
        baseQuery += " AND employee_id = %s" 
        filters.append(employee)
    
    pay_slip_list = frappe.db.sql(baseQuery, filters, as_dict=True)
    
    created_pay_slips = []

    for pay_slip in pay_slip_list:
        generated_name = str(uuid.uuid4())  # Generate a unique ID for the name field
        frappe.db.sql("""
            INSERT INTO `tabCreated Pay Slips` (
                `name`, `pay_slip`, `employee`,`employee_id`, `salary`, `parent`, `parenttype`, `parentfield`
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            generated_name,                 # name
            pay_slip['name'],               # pay_slip
            pay_slip['employee_name'],      # employee
            pay_slip['employee_id'],      # employee_id
            pay_slip['net_payble_amount'],  # salary
            parent_docname,                 # parent
            'Create Pay Slips',             # parenttype
            'created_pay_slips'             # parentfield
        ))
        if not any(item['pay_slip'] == pay_slip['name'] for item in created_pay_slips):
                    created_pay_slips.append({
                        'name': generated_name,
                        'pay_slip': pay_slip['name'],
                        'employee': pay_slip['employee_name'],
                        'employee_id': pay_slip['employee_id'],
                        'salary': pay_slip['net_payble_amount'],
                        'parent': parent_docname,
                        'parenttype': 'Create Pay Slips',
                        'parentfield': 'created_pay_slips'
                    })

    return created_pay_slips

# API to e-mail pay slips
@frappe.whitelist(allow_guest=True)
def email_pay_slip(pay_slips=None, raw_data=None):
    if pay_slips is None:
        pay_slips = []

    if raw_data is not None:
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON data provided in raw_data.")
    elif pay_slips:
        data = json.loads(pay_slips) 
    else:
        raise ValueError("Either raw_data or pay_slips must be provided.")

    for item in data:
        record = frappe.db.get_value("Created Pay Slips", item, "pay_slip")
        if record:
            pay_slips.append(record)
        if raw_data:
            data = pay_slips
    
    for pay_slip_name in data:
        if (pay_slip_name == "on"):
            continue
        doc = frappe.get_doc('Pay Slips', pay_slip_name)

        employee_name = doc.employee_name
        month = doc.month
        year = doc.year
        doctype = doc.doctype
        docname = doc.name
        personal_email = doc.personal_email

        subject = f"Pay Slip for {employee_name} - {month} {year}"

        # HTML email body with dynamic content
        context = {"doc": doc}  # Pass data to the template
        message = frappe.render_template("pinnacle/templates/email/pay_slip.html", context)
        
        # Attach the pay slip PDF
        if personal_email:
            frappe.sendmail(
                recipients=[personal_email],
                subject=subject,
                message=message,
                # header=["Pay Slip Notification", "green"]
            )
            return f"Email sent successfully to {personal_email} with the attached PDF: pay-slip-{doc.month}-{doc.employee_id}.pdf."
        else:
            frappe.throw(f"No email address found for employee {employee_name}")

# API to get pay slip report           
@frappe.whitelist(allow_guest=True)
def get_pay_slip_report(year=None,month=None, curr_user=None):
    
    user_roles = frappe.get_roles(curr_user)
    if 'All' in user_roles or 'HR User' in user_roles or 'HR Manager' in user_roles:
        records = frappe.db.sql("""
                                SELECT
                                        name,
                                        employee_name,
                                        personal_email,
                                        date_of_joining,
                                        basic_salary,
                                        standard_working_days,
                                        actual_working_days,
                                        full_day_working_days,
                                        sundays_working_days,
                                        half_day_working_days,
                                        three_four_quarter_days_working_days,
                                        quarter_day_working_days,
                                        lates_days,
                                        absent,
                                        full_day_working_amount,
                                        sunday_working_amount,
                                        half_day_working_amount,
                                        three_four_quarter_days_working_amount,
                                        quarter_day_working_amount,
                                        lates_amount,
                                        total,
                                        adjustments,
                                        other_earnings_amount,
                                        other_ernings_holidays_amount,
                                        net_payble_amount
                                FROM `tabPay Slips` WHERE year = %s AND month_num = %s
                            """,(year,month),as_dict=True)
        
        
    else:
        data = frappe.db.sql("""SELECT name FROM tabEmployee WHERE personal_email = %s  OR company_email = %s;""",(curr_user,curr_user),as_dict=True)
       
        if not data:
            return frappe.throw("No Employee Data found or you don't have access!")
        
        employee_id = data[0].get('name')
        records = frappe.db.sql("""
                                SELECT
                                        name,
                                        employee_name,
                                        personal_email,
                                        date_of_joining,
                                        basic_salary,
                                        standard_working_days,
                                        actual_working_days,
                                        full_day_working_days,
                                        sundays_working_days,
                                        half_day_working_days,
                                        three_four_quarter_days_working_days,
                                        quarter_day_working_days,
                                        lates_days,
                                        absent,
                                        full_day_working_amount,
                                        sunday_working_amount,
                                        half_day_working_amount,
                                        three_four_quarter_days_working_amount,
                                        quarter_day_working_amount,
                                        lates_amount,
                                        total,
                                        adjustments,
                                        other_earnings_amount,
                                        other_ernings_holidays_amount,
                                        net_payble_amount
                                FROM `tabPay Slips` WHERE year = %s AND month_num = %s AND employee_id = %s
                            """,(year,month,employee_id),as_dict=True)
    if not records:
        return frappe.msgprint(msg='No records found',title='Warning!')
    return records

    
    employee_name = pay_slip.employee_name
    month = pay_slip.month
    year = pay_slip.year
    doctype = pay_slip.doctype
    docname = pay_slip.name
    personal_email = pay_slip.personal_email
    
    subject = f"Pay Slip for {employee_name} - {month} {year}"
    
    message = f"""
    Dear {employee_name},
    Please find attached your pay slip for {month} {year}.
    Best regards,
    Your Company
    """
    
    pdf_attachment = frappe.attach_print(doctype, docname, file_name=f"Pay Slip {docname}")
    
    if personal_email:
        frappe.sendmail(
            recipients=[personal_email],
            subject=subject,
            message=message,
            attachments=[{
                'fname': f"Pay Slip - {employee_name}.pdf",
                'fcontent': pdf_attachment
            }],
        )
    else:
        frappe.throw(f"No email address found for employee {employee_name}")

#API to get pay slip for pay slip request
@frappe.whitelist(allow_guest=True)
def get_pay_slip_request(date=None,requested_by=None): 
    
    if date is None and requested_by is None:
        return frappe.throw("No date or requested by is not found")
    
    records = frappe.db.sql("""
                            SELECT name 
                            FROM `tabRequest Pay Slip` 
                            WHERE requested_date = %s OR  requested_by = %s;""",
                            (date,requested_by),as_dict=True)
    
    if not records:
        return frappe.throw("No requests found")
    
    return records

#API to print pay slip
@frappe.whitelist(allow_guest=True)
def print_pay_slip(pay_slips):
    try:
        pay_slips = json.loads(pay_slips)
        for pay_slip in pay_slips:
            frappe.utils.print_format.download_pdf('Pay Slips', pay_slip, format='Pay Slip Format')
    except Exception as e:
        frappe.log_error(message=str(e), title="Pay Slip Printing Error")
        frappe.throw(f"An error occurred while printing pay slips: {str(e)}")

#API get pay slip requests
@frappe.whitelist(allow_guest=True)
def getPaySlipRequests():
    records = frappe.db.get_all(
    "Request Pay Slip", 
    fields=["name", "requested_date", "employee", "year", "month", "status"],
    filters={"status": "Requested"},
    order_by="creation desc"
)

    return records

# API to approve pay slip request
@frappe.whitelist(allow_guest=True)
def approvePaySlipRequest(data):
    data = json.loads(data)
    
    # Check if a Pay Slip exists for the given employee, month, and year
    if frappe.db.exists("Pay Slips", {
        'employee_id': data['select_employee'],
        'month_num': data['month'],
        'year': data['year']
    }):
        # Fetch the Pay Slip document
        paySlip = frappe.get_doc("Pay Slips", {
            'employee_id': data['select_employee'],
            'month_num': data['month'],
            'year': data['year']
        })
    else:
       createPaySlips(data)
       paySlip = frappe.get_doc("Pay Slips", {
            'employee_id': data['select_employee'],
            'month_num': data['month'],
            'year': data['year']
        })
    
    employee_name = paySlip.employee_name
    month = paySlip.month
    year = paySlip.year
    doctype = paySlip.doctype
    docname = paySlip.name
    personal_email = paySlip.personal_email
    subject = f"Pay Slip for {employee_name} - {month} {year}"
    message = f"""
    Dear {employee_name},
    Please find attached your pay slip for {month} {year}.
    Best regards,
    Your Company
    """
    pdf_attachment = frappe.attach_print(doctype, docname, file_name=f"Pay Slip {docname}")
    
    if personal_email:
        frappe.sendmail(
            recipients=[personal_email],
            subject=subject,
            message=message,
            attachments=[{
                'fname': f"Pay Slip - {employee_name}.pdf",
                'fcontent': pdf_attachment
            }],
        )
        return {"message": _("Success")}
    else:
        frappe.throw(f"No email address found for employee {employee_name}")

# API to regenerate pay slip
@frappe.whitelist(allow_guest=True)
def regeneratePaySlip(data):
    
    data = json.loads(data)
    year = data.get('year')
    month = data.get('month')
    
    empRecords = getEmpRecords(data)
    employeeData = calculateMonthlySalary(empRecords,year,month)
    
    for emp_id, data in employeeData.items():
        
        month_mapping = {
                1: "January",
                2: "February",
                3: "March",
                4: "April",
                5: "May",
                6: "June",
                7: "July",
                8: "August",
                9: "September",
                10: "October",
                11: "November",
                12: "December"
            }
        month_name = month_mapping.get(month)
        
        salary_info = data.get("salary_information", {})
        
        full_day_working_amount = round((salary_info.get("full_days", 0) * salary_info.get("per_day_salary", 0)), 2)
        quarter_day_working_amount = round((salary_info.get("quarter_days", 0) * salary_info.get("per_day_salary", 0) * .75), 2)
        half_day_working_amount = round((salary_info.get("half_days", 0) * .5 * salary_info.get("per_day_salary", 0)), 2)
        three_four_quarter_days_working_amount = round((salary_info.get("three_four_quarter_days", 0) * .25 * salary_info.get("per_day_salary", 0)), 2)
        lates_amount = round((salary_info.get("lates", 0) * salary_info.get("per_day_salary", 0) * .1), 2)
        other_earnings_amount = round((salary_info.get("overtime", 0)), 2) + salary_info.get("holidays")
        
        # Check if a Pay Slip already exists for the employee
        existing_doc = frappe.get_all('Pay Slips', filters={
            'employee_id': data.get("employee"),
            'docstatus': 0  # Check for open or draft status
        }, fields=['name'])

        if existing_doc:
            # If a Pay Slip exists, update it
            pay_slip = frappe.get_doc('Pay Slips', existing_doc[0]['name'])
        else:
            # If no Pay Slip exists, create a new one
            pay_slip = frappe.new_doc('Pay Slips')
            
        
        # Update the fields
        pay_slip.update({
          'year': year,
          'month': month_name,
          'company': data.get("company"),
          'employee_id': data.get("employee"),
          'employee_name': data.get("employee_name"),
          'personal_email': data.get("personal_email"),
          'designation': data.get("designation"),
          'department': data.get("department"),
          'pan_number': data.get("pan_number"),
          'date_of_joining': data.get("date_of_joining"),
          'attendance_device_id': data.get("attendance_device_id"),
          'basic_salary': data.get("basic_salary"),
          'per_day_salary': salary_info.get("per_day_salary"),
          'standard_working_days': salary_info.get("standard_working_days"),
          'full_day_working_days': salary_info.get("full_days"),
          "full_days_working_rate": salary_info.get("per_day_salary"),
          "full_day_working_amount": full_day_working_amount,
          'quarter_day_working_days': salary_info.get("quarter_days"),
          'quarter_day_working_rate': salary_info.get("per_day_salary"),
          'quarter_day_working_amount': quarter_day_working_amount,
          'half_day_working_days': salary_info.get("half_days"),
          'half_day_working_rate': salary_info.get("per_day_salary"),
          'half_day_working_amount': half_day_working_amount,
          'three_four_quarter_days_working_days': salary_info.get("three_four_quarter_days"),
          'three_four_quarter_days_rate': salary_info.get("per_day_salary"),
          'three_four_quarter_days_working_amount': three_four_quarter_days_working_amount,
          'lates_days': salary_info.get("lates"),
          'lates_rate': salary_info.get("per_day_salary"),
          'lates_amount': lates_amount,
          'absent': salary_info.get("absent"),
          'sundays_working_days': salary_info.get("sundays_working_days"),
          'sunday_working_amount': salary_info.get("sundays_salry"),
          'sunday_working_rate':salary_info.get("per_day_salary"),
          'actual_working_days': salary_info.get("actual_working_days"),
          'net_payble_amount': salary_info.get("total_salary"),
          'other_earnings_overtime': salary_info.get("overtime"),
          'other_earnings_amount': other_earnings_amount,
          'other_ernings_holidays_amount': salary_info.get("holidays"),
          'total': round(((full_day_working_amount + quarter_day_working_amount + half_day_working_amount + three_four_quarter_days_working_amount) - lates_amount), 2),
        })
        
        # Save or submit the document
        pay_slip.save()
        
        frappe.db.sql(
            """UPDATE `tabCreated Pay Slips` SET salary = %s WHERE pay_slip = %s AND employee_id = %s""",
            (pay_slip.net_payble_amount, pay_slip.name, pay_slip.employee_id)
        )

        # frappe.db.commit()
        
        
    return {"message": _("Success")}

import frappe
import frappe.defaults
from frappe import _
import json
import uuid
from frappe import sendmail
from collections import defaultdict
from frappe.core.doctype.communication.email import make
import frappe.utils
import frappe.utils.print_format
from pinnacle.pinnaclehrms.salary_calculation import calculate_monthly_salary
from pinnacle.pinnaclehrms.doctype.create_pay_slips.create_pay_slips import CreatePaySlips

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
def get_pay_slip_list(month, parent_docname):
    pay_slip_list = frappe.db.sql("""
        SELECT name, employee_name, net_payble_amount 
        FROM `tabPay Slips` 
        WHERE month_num = %s
    """, (month,), as_dict=True)
    
    created_pay_slips = []

    for pay_slip in pay_slip_list:
        generated_name = str(uuid.uuid4())  # Generate a unique ID for the name field
        frappe.db.sql("""
            INSERT INTO `tabCreated Pay Slips` (
                `name`, `pay_slip`, `employee`, `salary`, `parent`, `parenttype`, `parentfield`
            ) VALUES (%s, %s, %s, %s, %s, %s, %s);
        """, (
            generated_name,                 # name
            pay_slip['name'],               # pay_slip
            pay_slip['employee_name'],      # employee
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
        doc = frappe.get_doc('Pay Slips', pay_slip_name)

        employee_name = doc.employee_name
        month = doc.month
        year = doc.year
        doctype = doc.doctype
        docname = doc.name
        personal_email = doc.personal_email

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

# API to approve pay slip request
@frappe.whitelist(allow_guest=True)
def approve_pay_slip_req(employee,month,year):
    
    self = []
    if frappe.db.exists("Pay Slips", {'employee_id':employee,'month_num':month,'year':year}):
        pay_slip = frappe.get_doc("Pay Slips",{'employee_id':employee,'month_num':month,'year':year})
    else:
        if month == 2:
            # Check for leap year
            if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                working_days = 29
            else:
                working_days = 28
        elif month in [4, 6, 9, 11]:
            working_days = 30
        else:
            working_days = 31
            
        holidays = frappe.db.sql("""SELECT holiday_date FROM tabHoliday WHERE MONTH(holiday_date) = %s AND YEAR(holiday_date) = %s """,(month, year),as_dict=True)
        base_query = """
            SELECT
                e.company,
                e.employee,
                e.employee_name,
                e.personal_email,
                e.designation,
                e.department,
                e.pan_number,
                e.date_of_joining,
                e.grade,
                e.attendance_device_id,
                e.default_shift,
                a.attendance_date,
                a.in_time,
                a.out_time
            FROM
                tabEmployee e
            JOIN
                tabAttendance a ON e.employee = a.employee
            WHERE
                YEAR(a.attendance_date) = %s AND MONTH(a.attendance_date) = %s AND e.employee = %s
        """
        filters = [year, month, employee]
        records = frappe.db.sql(base_query, filters, as_dict=False)
        if not records:
            return frappe.throw("No records found!")
        
        # Initialize a defaultdict to organize employee records
        emp_records = defaultdict(lambda: {
            "company":"",
            "employee": "",
            "employee_name": "",
            "personal_email": "",
            "designation": "",
            "department": "",
            "pan_number": "",
            "date_of_joining": "",
            "basic_salary": 0,
            "attendance_device_id": "",
            "attendance_records": [],
            "salary_information": {}
        })
        
        # Populate employee records from the query results
        for record in records:
            (
                company,employee_id, employee_name, personal_email, designation, department,
                pan_number, date_of_joining, grade, attendance_device_id, shift,
                attendance_date, in_time, out_time
            ) = record
            basic_salary = frappe.db.get_value('Employee Grade', { 'name':grade}, ['default_base_pay'])
            if emp_records[employee_id]["employee"]:
                # Employee already exists, append to attendance_records
                emp_records[employee_id]["attendance_records"].append({
                    "attendance_date": attendance_date,
                    "shift":shift,
                    "in_time": in_time,
                    "out_time": out_time
                })
            else:
                # Add new employee data
                emp_records[employee_id] = {
                    "company":company,
                    "employee": employee_id,
                    "employee_name": employee_name,
                    "personal_email": personal_email,
                    "designation": designation,
                    "department": department,
                    "pan_number": pan_number,
                    "date_of_joining": date_of_joining,
                    "basic_salary": basic_salary,
                    "attendance_device_id": attendance_device_id,
                    "shift":shift,
                    "attendance_records": [{
                        "attendance_date": attendance_date,
                        "shift":shift,
                        "in_time": in_time,
                        "out_time": out_time
                    }],
                    "salary_information": {}
                }
        
        # Calculate monthly salary for each employe
        employee_data = calculate_monthly_salary(emp_records, working_days,holidays)
        # Create pay slips and save them
        # frappe.msgprint(str(dict(employee_data)))
        CreatePaySlips.create_pay_slips(self,employee_data,month,year)
        pay_slip = frappe.get_doc("Pay Slips",{'employee_id':employee,'month_num':month,'year':year})
    
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
    return frappe.msgprint("Coming Soon!")
    pay_slips = json.loads(pay_slips)
    for pay_slip in pay_slips:
        frappe.utils.print_format.download_pdf('Pay Slips', pay_slip, format='Pay Slip Format')

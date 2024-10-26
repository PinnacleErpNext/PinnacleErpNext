import frappe
from collections import defaultdict
from pinnacle.salary_calculation import calculate_monthly_salary

@frappe.whitelist(allow_guest=True)
def regenerate_pay_slip(selected_year, selected_month, selected_emp=None, selected_company=None):
    month = int(selected_month)
    year = int(selected_year)
    company = selected_company
    emplyee = selected_emp
    
    holidays = frappe.db.sql("""
                                 SELECT holiday_date
                                FROM tabHoliday
                                WHERE MONTH(holiday_date) = %s
                                AND YEAR(holiday_date) = %s
                                 """,(month, year),as_dict=True)
    
    # Determine the number of working days in the month
    if month == 2:
        # Check for leap year
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            total_working_days = 29
        else:
            total_working_days = 28
    elif month in [4, 6, 9, 11]:
        total_working_days = 30
    else:
        total_working_days = 31

    # Construct the base query
    base_query = """
    SELECT
        e.employee,
        e.employee_name,
        e.personal_email,
        e.company,
        e.designation,
        e.department,
        e.pan_number,
        e.date_of_joining,
        e.grade,
        e.attendance_device_id,
        a.shift,
        a.attendance_date,
        a.in_time,
        a.out_time
    FROM
        tabEmployee e
    JOIN
        tabAttendance a ON e.employee = a.employee
    WHERE
        YEAR(a.attendance_date) = %s AND MONTH(a.attendance_date) = %s
    """
    
    # Add the company filter if provided
    filters = [year, month]
    if company:
        base_query += " AND a.company = %s"
        filters.append(company)
    if emplyee:
        base_query += " AND e.employee = %s"
        filters.append(emplyee)

    # Execute the query
    records = frappe.db.sql(base_query, filters, as_dict=True)

    # Initialize a defaultdict to organize employee records
    emp_records = defaultdict(lambda: {
        "employee": "",
        "employee_name": "",
        "personal_email": "",
        "company":"",
        "designation": "",
        "department": "",
        "pan_number": "",
        "date_of_joining": "",
        "grade": "",
        "attendance_device_id": "",
        "attendance_records": [],
        "salary_information": {}
    })

    # Populate employee records from the query results
    for record in records:
        employee_id = record.get('employee')
        attendance_date = record.get('attendance_date')
        shift = record.get('shift')
        in_time = record.get('in_time')
        out_time = record.get('out_time')

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
            grade = record.get('grade')
            basic_salary = frappe.db.get_value('Salary Structure Assignment', {'employee': employee_id, 'grade':grade}, ['base'])
            emp_records[employee_id] = {
                "company":record.get('company'),
                "employee": employee_id,
                "employee_name": record.get('employee_name'),
                "personal_email": record.get('personal_email'),
                "designation": record.get('designation'),
                "department": record.get('department'),
                "pan_number": record.get('pan_number'),
                "date_of_joining": record.get('date_of_joining'),
                "basic_salary": basic_salary,
                "attendance_device_id": record.get('attendance_device_id'),
                "attendance_records": [{
                    "attendance_date": attendance_date,
                    "shift":shift,
                    "in_time": in_time,
                    "out_time": out_time
                }],
                "salary_information": {}
            }

    # Calculate monthly salary for each employee
    employee_data = calculate_monthly_salary(emp_records, total_working_days, holidays, year, month)

    for emp_id, data in employee_data.items():
        
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
        
        frappe.msgprint(f"Pay Slip created for {data.get('employee')}")

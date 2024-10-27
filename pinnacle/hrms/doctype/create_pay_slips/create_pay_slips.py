# Copyright (c) 2024, mygstcafe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from collections import defaultdict
from pinnacle.hrms.doctype.salary_calculation import calculate_monthly_salary

class CreatePaySlips(Document):
    
    def autoname(self):
        if self.genrate_for_all:
            self.name = f"For-all-pay-slip-{self.year}-{self.month}"

    def get_emp_records(self):
        
        if not self.month or not self.year:
            return frappe.throw("Select year and month")
        
        year = self.year
        month = int(self.month)
        
        
        holidays = frappe.db.sql("""
                                SELECT holiday_date FROM tabHoliday 
                                WHERE MONTH(holiday_date) = %s AND YEAR(holiday_date) = %s """,
                                (month, year),as_dict=True)

        # Determine the number of working days in the month
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
        
        # Construct the base query
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
                YEAR(a.attendance_date) = %s AND MONTH(a.attendance_date) = %s
        """
        
        filters = [year, month]
        if not self.genrate_for_all :
            if not self.select_company and not self.select_employee:
                return frappe.throw("Please Select Company or emplyee!")
        
            if self.select_company:
                company = self.select_company
                base_query += "AND e.company = %s"
                filters.append(company)
            else:
                employee = self.select_employee
                base_query += "AND e.employee = %s"
                filters.append(employee)
              
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
        # frappe.throw(str(dict(emp_records)))
        employee_data = calculate_monthly_salary(emp_records, working_days,holidays,year,month)
        # Create pay slips and save them
        # frappe.throw(str(dict(employee_data)))
        self.create_pay_slips(employee_data,month,year)

    def create_pay_slips(self, employee_data, month, year):
        for emp_id, data in employee_data.items():
            salary_info = data.get("salary_information", {})
            
            full_day_working_amount = round((salary_info.get("full_days", 0) * salary_info.get("per_day_salary", 0)), 2)
            quarter_day_working_amount = round((salary_info.get("quarter_days", 0) * salary_info.get("per_day_salary", 0) * .75), 2)
            half_day_working_amount = round((salary_info.get("half_days", 0) * .5 * salary_info.get("per_day_salary", 0)), 2)
            three_four_quarter_days_working_amount = round((salary_info.get("three_four_quarter_days", 0) * .25 * salary_info.get("per_day_salary", 0)), 2)
            lates_amount = round((salary_info.get("lates", 0) * salary_info.get("per_day_salary", 0) * .1), 2)
            other_earnings_amount = round((salary_info.get("overtime", 0)), 2) + salary_info.get("holidays")
            
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

            # Create a new Pay Slip document
            new_doc = frappe.get_doc({
                'doctype': 'Pay Slips',
                'docstatus': 0,
                'year': year,
                'month': month_name,
                'month_num':month,
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
                'sunday_working_amount': salary_info.get("sundays_salary"),
                'sunday_working_rate':salary_info.get("per_day_salary"),
                'actual_working_days': salary_info.get("actual_working_days"),
                'net_payble_amount': salary_info.get("total_salary"),
                'other_earnings_overtime': salary_info.get("overtime"),
                'other_earnings_amount': other_earnings_amount,
                'total': round(((full_day_working_amount + quarter_day_working_amount + half_day_working_amount + three_four_quarter_days_working_amount) - lates_amount), 2),
                'other_ernings_holidays_amount': salary_info.get("holidays"),
            })
            
            # Insert the new document to save it in the database
            new_doc.insert()
            
            frappe.msgprint(f"Pay Slip created for {data.get('employee')}")

    def before_save(self):
        self.get_emp_records()

    # def on_submit(self):
    #     self.add_regenrate_button = 0
    #     pay_slip_list = self.created_pay_slips
        
    #     for item in pay_slip_list:
    #         docname = item.pay_slip
    #         pay_slip = frappe.get_doc("Pay Slips", docname)
            
    #         pay_slip.submit()
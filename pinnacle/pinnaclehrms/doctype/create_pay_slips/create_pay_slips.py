# Copyright (c) 2024, mygstcafe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from collections import defaultdict
from pinnacle.pinnaclehrms.salary_calculation import calculate_monthly_salary

class CreatePaySlips(Document):
    
    def autoname(self):
        if self.genrate_for_all:
            self.name = f"For-all-pay-slip-{self.year}-{self.month}"

    def get_emp_records(self):
        
        if not self.month or not self.year:
            return frappe.throw("Select year and month")
        
        year = self.year
        month = int(self.month)
        
        date = f"{year}-{month:02d}-01"
        
        holidays = frappe.db.sql("""
                                SELECT holiday_date FROM tabHoliday 
                                WHERE MONTH(holiday_date) = %s AND YEAR(holiday_date) = %s """,
                                (month, year),as_dict=True)

        # Determine the number of working days in the month
        if month == 2:
            # Check for leap year
            if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
                workingDays = 29
            else:
                workingDays = 28
        elif month in [4, 6, 9, 11]:
            workingDays = 30
        else:
            workingDays = 31
        
        # Construct the base query
        baseQuery = """
            SELECT
                e.company,
                e.employee,
                e.employee_name,
                e.personal_email,
                e.designation,
                e.department,
                e.pan_number,
                e.date_of_joining,
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
                baseQuery += "AND e.company = %s"
                filters.append(company)
            if self.select_employee:
                employee = self.select_employee
                baseQuery += "AND e.employee = %s"
                filters.append(employee)
              
        records = frappe.db.sql(baseQuery, filters, as_dict=False)
        
        if not records:
            return frappe.throw("No records found!")
        
        # Initialize a defaultdict to organize employee records
        empRecords = defaultdict(lambda: {
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
                pan_number, date_of_joining, attendance_device_id, shift,
                attendance_date, in_time, out_time
            ) = record
            salaryData = frappe.db.sql("""
                                        SELECT tsh.salary, tas.eligible_for_overtime_salary
                                        FROM `tabSalary History` AS tsh
                                        JOIN `tabAssign Salary` AS tas ON tsh.parent = tas.name
                                        WHERE tas.employee_id = %s
                                        AND tsh.from_date <= %s
                                        ORDER BY tsh.from_date DESC 
                                        LIMIT 1
                                    """, (employee_id,date), as_dict=True)

            # Extract the salary value if the result is not empty
            basicSalary = salaryData[0].salary
            isOvertime = salaryData[0].eligible_for_overtime_salary

            if empRecords[employee_id]["employee"]:
                # Employee already exists, append to attendance_records
                empRecords[employee_id]["attendance_records"].append({
                    "attendance_date": attendance_date,
                    "shift":shift,
                    "in_time": in_time,
                    "out_time": out_time
                })
            else:
                # Add new employee data
                empRecords[employee_id] = {
                    "company":company,
                    "employee": employee_id,
                    "employee_name": employee_name,
                    "personal_email": personal_email,
                    "designation": designation,
                    "department": department,
                    "pan_number": pan_number,
                    "date_of_joining": date_of_joining,
                    "basic_salary": basicSalary,
                    "is_overtime":isOvertime,
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
        employeeData = calculate_monthly_salary(empRecords, workingDays,holidays,year,month)
        # Create pay slips and save them
        # frappe.throw(str(dict(employeeData)))
        self.create_pay_slips(employeeData,month,year)

    def create_pay_slips(self, employeeData, month, year):
        for emp_id, data in employeeData.items():
            salaryInfo = data.get("salary_information", {})
            
            fullDayWorkingAmount = round((salaryInfo.get("full_days", 0) * salaryInfo.get("per_day_salary", 0)), 2)
            quarterDayWorkingAmount = round((salaryInfo.get("quarter_days", 0) * salaryInfo.get("per_day_salary", 0) * .75), 2)
            halfDayWorkingAmount = round((salaryInfo.get("half_days", 0) * .5 * salaryInfo.get("per_day_salary", 0)), 2)
            threeFourQuarterDaysWorkingAmount = round((salaryInfo.get("three_four_quarter_days", 0) * .25 * salaryInfo.get("per_day_salary", 0)), 2)
            latesAmount = round((salaryInfo.get("lates", 0) * salaryInfo.get("per_day_salary", 0) * .1), 2)
            otherEarningsAmount = round((salaryInfo.get("overtime", 0)), 2) + salaryInfo.get("holidays")
            
            monthMapping = {
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
            monthName = monthMapping.get(month)

            # Create a new Pay Slip document
            new_doc = frappe.get_doc({
                'doctype': 'Pay Slips',
                'docstatus': 0,
                'year': year,
                'month': monthName,
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
                'per_day_salary': salaryInfo.get("per_day_salary"),
                'standard_working_days': salaryInfo.get("standard_working_days"),
                'full_day_working_days': salaryInfo.get("full_days"),
                "full_days_working_rate": salaryInfo.get("per_day_salary"),
                "full_day_working_amount": fullDayWorkingAmount,
                'quarter_day_working_days': salaryInfo.get("quarter_days"),
                'quarter_day_working_rate': salaryInfo.get("per_day_salary"),
                'quarter_day_working_amount': quarterDayWorkingAmount,
                'half_day_working_days': salaryInfo.get("half_days"),
                'half_day_working_rate': salaryInfo.get("per_day_salary"),
                'half_day_working_amount': halfDayWorkingAmount,
                'three_four_quarter_days_working_days': salaryInfo.get("three_four_quarter_days"),
                'three_four_quarter_days_rate': salaryInfo.get("per_day_salary"),
                'three_four_quarter_days_working_amount': threeFourQuarterDaysWorkingAmount,
                'lates_days': salaryInfo.get("lates"),
                'lates_rate': salaryInfo.get("per_day_salary"),
                'lates_amount': latesAmount,
                'absent': salaryInfo.get("absent"),
                'sundays_working_days': salaryInfo.get("sundays_working_days"),
                'sunday_working_amount': salaryInfo.get("sundays_salary"),
                'sunday_working_rate':salaryInfo.get("per_day_salary"),
                'actual_working_days': salaryInfo.get("actual_working_days"),
                'net_payble_amount': salaryInfo.get("total_salary"),
                'other_ernings_overtime_amount': salaryInfo.get("overtime"),
                'other_earnings_amount': otherEarningsAmount,
                'total': round(((fullDayWorkingAmount + quarterDayWorkingAmount + halfDayWorkingAmount + threeFourQuarterDaysWorkingAmount) - latesAmount), 2),
                'other_ernings_holidays_amount': salaryInfo.get("holidays"),
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
    
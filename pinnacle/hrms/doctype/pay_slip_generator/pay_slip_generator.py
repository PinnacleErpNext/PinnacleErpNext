# Copyright (c) 2024, mygstcafe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from collections import defaultdict
from pinnacle.salary_calculation import calculate_monthly_salary

class PaySlipGenerator(Document):

    def get_emp_records(self):
        company = self.select_company
        year = self.year
        month = self.month

        # Calculate the total working days
        total_working_days = self.working_days
        
        # Construct the base query
        base_query = """
            SELECT
                e.employee,
                e.employee_name,
                e.personal_email,
                e.designation,
                e.department,
                e.pan_number,
                e.date_of_joining,
                e.basic_salary,
                e.attendance_device_id,
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
        
        records = frappe.db.sql(base_query, filters, as_dict=False)
        
        # Initialize a defaultdict to organize employee records
        emp_records = defaultdict(lambda: {
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
                employee_id, employee_name, personal_email, designation, department,
                pan_number, date_of_joining, basic_salary, attendance_device_id,
                attendance_date, in_time, out_time
            ) = record
            
            if emp_records[employee_id]["employee"]:
                # Employee already exists, append to attendance_records
                emp_records[employee_id]["attendance_records"].append({
                    "attendance_date": attendance_date,
                    "in_time": in_time,
                    "out_time": out_time
                })
            else:
                # Add new employee data
                emp_records[employee_id] = {
                    "employee": employee_id,
                    "employee_name": employee_name,
                    "personal_email": personal_email,
                    "designation": designation,
                    "department": department,
                    "pan_number": pan_number,
                    "date_of_joining": date_of_joining,
                    "basic_salary": basic_salary,
                    "attendance_device_id": attendance_device_id,
                    "attendance_records": [{
                        "attendance_date": attendance_date,
                        "in_time": in_time,
                        "out_time": out_time
                    }],
                    "salary_information": {}
                }
                
        # Calculate monthly salary for each employee
        employee_data = calculate_monthly_salary(emp_records, total_working_days)
        
        # Create pay slips and save them
        self.create_pay_slips(employee_data)

    def create_pay_slips(self, employee_data):
        for emp_id, data in employee_data.items():
            salary_info = data.get("salary_information", {})
            
            # Create a new Pay Slip document
            new_doc = frappe.get_doc({
                'doctype': 'Pay Slips',
                'docstatus': 0,
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
                'full_day_workings': salary_info.get("full_days"),
                'three_quarter_days_workings': salary_info.get("three_quarter_days"),
                'half_days_workings': salary_info.get("half_days"),
                'quarter_days_workings': salary_info.get("quarter_days"),
                'lates': salary_info.get("lates"),
                'absent': salary_info.get("absent"),
                'actual_working_days': salary_info.get("actual_working_days"),
                'total_monthly_salary': salary_info.get("total_salary"),
                'overtime': salary_info.get("overtime"),
            })
            
            # Insert the new document to save it in the database
            new_doc.insert()
            
            frappe.msgprint(f"Pay Slip created for {data.get('employee')}")

    def before_save(self):
        self.get_emp_records()

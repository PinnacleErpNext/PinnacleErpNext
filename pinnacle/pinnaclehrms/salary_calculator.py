import frappe
import json
from datetime import datetime, time
from collections import defaultdict
from dateutil.relativedelta import relativedelta


def createPaySlips(data):
        # return frappe.throw(str(data))
        year = data.get('year')
        month = data.get('month')
        
        empRecords = getEmpRecords(data)
        
        employeeData = calculateMonthlySalary(empRecords,year, month)
        
        for emp_id, data in employeeData.items():
            if frappe.db.exists("Pay Slips", {'employee_id': data.get("employee"), 'month_num': month, 'year': year}):
                continue
            else:
                salaryInfo = data.get("salary_information", {})
                
                # Calculations
                fullDayWorkingAmount = round((salaryInfo.get("full_days", 0) * salaryInfo.get("per_day_salary", 0)), 2)
                earlyCheckoutWorkingAmount = round((salaryInfo.get("early_checkout_days", 0) * salaryInfo.get("per_day_salary", 0)), 2)
                quarterDayWorkingAmount = round((salaryInfo.get("quarter_days", 0) * salaryInfo.get("per_day_salary", 0) * .75), 2)
                halfDayWorkingAmount = round((salaryInfo.get("half_days", 0) * .5 * salaryInfo.get("per_day_salary", 0)), 2)
                threeFourQuarterDaysWorkingAmount = round((salaryInfo.get("three_four_quarter_days", 0) * .25 * salaryInfo.get("per_day_salary", 0)), 2)
                latesAmount = round((salaryInfo.get("lates", 0) * salaryInfo.get("per_day_salary", 0) * .1), 2)
                otherEarningsAmount = round((salaryInfo.get("overtime", 0)), 2) + salaryInfo.get("holidays") + salaryInfo.get("leave_encashment")
                
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
                    'month_num': month,
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
                    'early_checkout_working_days': salaryInfo.get("early_checkout_days"),
                    "early_checkout_working_rate": salaryInfo.get("per_day_salary"),
                    "early_checkout_working_amount": earlyCheckoutWorkingAmount,
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
                    'sunday_working_rate': salaryInfo.get("per_day_salary"),
                    'actual_working_days': salaryInfo.get("actual_working_days"),
                    'net_payble_amount': salaryInfo.get("total_salary"),
                    'other_ernings_overtime_amount': salaryInfo.get("overtime"),
                    'other_earnings_amount': otherEarningsAmount,
                    'total': round(((fullDayWorkingAmount + quarterDayWorkingAmount + halfDayWorkingAmount + threeFourQuarterDaysWorkingAmount) - latesAmount), 2),
                    'other_ernings_holidays_amount': salaryInfo.get("holidays"),
                    'other_earnings_leave_encashent': salaryInfo.get("leave_encashment")
                })
                
                
                # Insert the new document to save it in the database
                new_doc.insert()

def getEmpRecords(data):
        
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
        
        year = data.get('year')
        month = int(data.get('month'))
        
            
        if not year or not month:
            return frappe.throw("Select year and month")

        filters = [year, month]
            
        autoCalculateLeaveEncashment = data.get('auto_calculate_leave_encashment')
        lates = data.get('allowed_lates')
            
            # Check for company or employee selection

        if data.get('select_company'):
            company = data.get('select_company')
            baseQuery += "AND e.company = %s"
            filters.append(company)
        if data.get('select_employee'):
            employee = data.get('select_employee')
            baseQuery += "AND e.employee = %s"
            filters.append(employee)
        
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
            "auto_calculate_leave_encashment":"",
            "lates":"",
            "holidays":"",
            "working_days":"",
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
            if salaryData:
                basicSalary = salaryData[0].salary
                isOvertime = salaryData[0].eligible_for_overtime_salary
            else:
                return frappe.throw(f"No salary found for employee {employee_id}")
            
            
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
                    "auto_calculate_leave_encashment":autoCalculateLeaveEncashment,
                    "lates":lates,
                    "holidays":holidays,
                    "working_days":workingDays,
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
        
        return empRecords
        
def calculateMonthlySalary(employeeData,year, month):
    
    month = int(month)
    year = int(year)
    
    if month >= 4:
        # Financial year starts in the current year and ends in the next year
        startYear = year
        endYear = year + 1
    else:
        # Financial year starts in the previous year and ends in the current year
        startYear = year - 1
        endYear = year
        
    # Define start and end dates of the financial year
    startDate = datetime(startYear, 4, 1)
    endDate = datetime(endYear, 3, 31)
    
    for emp_id, data in employeeData.items():
        
        totalSalary = 0.0
        totalLateDeductions = 0.0
        fullDays = 0
        halfDays = 0
        quarterDays = 0
        threeFourQuarterDays = 0
        totalAbsents = 0
        lates = 0
        sundays = 0
        sundaysSalary = 0.0
        overtimeSalary = 0.0
        actualWorkingDays = 0
        leaveEncashment = 0
        earlyCheckOutDays = 0
        
        basicSalary = data.get("basic_salary", 0)
        attendanceRecords = data.get("attendance_records", [])
        isOvertime = data.get("is_overtime")
        autoCalculateLeaveEncashment = data.get("auto_calculate_leave_encashment")
        allowedLates = data.get("lates")
        holidays = data.get("holidays")
        totalWorkingDays = data.get("working_days")
        
        shiftVariationRecord = frappe.db.sql("""
                                    SELECT svh.date AS attendance_date, svh.in_time, svh.out_time
                                    FROM `tabShift Variation` AS sv
                                    JOIN `tabShift Variation History` AS svh ON sv.name = svh.parent
                                    WHERE sv.year = %s AND sv.month_num = %s;
                                      """, (year, month), as_dict=True)
        
        shiftVariation = {
                            record['attendance_date']: record for record in shiftVariationRecord
                        }
        
        dojStr = data.get('date_of_joining')
        doj = datetime.strptime(dojStr, "%Y-%m-%d") if isinstance(dojStr, str) else dojStr
        
        currentDate = datetime.today().date()
        workingPeriod = (relativedelta(currentDate, doj)).years
        
        
        if autoCalculateLeaveEncashment and workingPeriod>=1:
    
            leaveEncashmentData = frappe.db.sql("""
                                        SELECT 
                                            AVG(tsh.salary) AS avgSalary, tas.paid_leaves AS paidLeaves
                                        FROM 
                                            `tabSalary History` AS tsh 
                                        JOIN 
                                            `tabAssign Salary` AS tas 
                                        ON 
                                            tsh.parent = tas.name 
                                        WHERE 
                                            tas.employee_id = %s 
                                        AND YEAR(tsh.from_date) BETWEEN %s AND %s
                                          """,(data.get('employee'),startYear,endYear),as_dict=True)
            
            averageSalary = leaveEncashmentData[0].avgSalary
            paidLeaves = leaveEncashmentData[0].paidLeaves/86400
            
            perDaySalary = averageSalary/ 30
            
            if doj.year < startDate.year:
                calFrmDate = startDate
                difference = relativedelta(endDate, calFrmDate)
                leaveEncashmentMonths = difference.years * 12 + difference.months +1
            else:
                calFrmDate = doj
                difference = relativedelta(endDate, calFrmDate)
                leaveEncashmentMonths = difference.years * 12 + difference.months
            
            leaveEncashment = ((paidLeaves / 12) * leaveEncashmentMonths) * perDaySalary
            print(f"Leave Encashment: {leaveEncashment}")
        
        perDaySalary = round(basicSalary / totalWorkingDays, 2)
        
        for day in range(1, totalWorkingDays + 1):
            today = datetime(year, month, day).date()
            
            attendanceRecord = next((record for record in attendanceRecords if record['attendance_date'] == today), None)
            
            attendanceDate = today
            
            if attendanceRecord:
                attendanceDate = attendanceRecord["attendance_date"]
                inTime = attendanceRecord["in_time"]
                outTime = attendanceRecord["out_time"]
                
                if attendanceDate in shiftVariation:
                    shiftVariationData = shiftVariation[attendanceDate]
                    shiftStart = shiftVariationData.in_time
                    shiftEnd = shiftVariationData.out_time
                    
                    startHours, remainder = divmod(shiftStart.seconds, 3600)
                    startMinutes, _ = divmod(remainder, 60)
                    endHours, remainder = divmod(shiftEnd.seconds, 3600)
                    endMinutes, _ = divmod(remainder, 60)
                    
                    idealCheckInTime = datetime.combine(attendanceDate, time(startHours, startMinutes))
                    idealCheckOutTime = datetime.combine(attendanceDate, time(endHours, endMinutes))
                    overtimeThreshold = datetime.combine(attendanceDate, time(19, 30))
                    
                    idealWorkingTime = idealCheckOutTime - idealCheckInTime
                    idealWorkingHours = idealWorkingTime.total_seconds() / 3600
                    
                else:
                    shift = attendanceRecord["shift"]
                    
                    
                    shiftStart = frappe.db.get_value('Shift Type', {"name": shift}, "start_time")
                    shiftEnd = frappe.db.get_value('Shift Type', {"name": shift}, "end_time")
                    
                    startHours, remainder = divmod(shiftStart.seconds, 3600)
                    startMinutes, _ = divmod(remainder, 60)
                    endHours, remainder = divmod(shiftEnd.seconds, 3600)
                    endMinutes, _ = divmod(remainder, 60)
                    
                    idealCheckInTime = datetime.combine(attendanceDate, time(startHours, startMinutes))
                    idealCheckOutTime = datetime.combine(attendanceDate, time(endHours, endMinutes))
                    overtimeThreshold = datetime.combine(attendanceDate, time(19, 30))
                    
                    idealWorkingTime = idealCheckOutTime - idealCheckInTime
                    idealWorkingHours = idealWorkingTime.total_seconds() / 3600
                
                if inTime and outTime:
                    checkIn = datetime.combine(attendanceDate, inTime.time())
                    checkOut = datetime.combine(attendanceDate, outTime.time())
                    
                    totalWorkingTime = checkOut - checkIn
                    totalWorkingHours = round((totalWorkingTime.total_seconds() / 3600),2)
                    
                    if idealWorkingHours <= totalWorkingHours:
                        if totalWorkingHours > idealWorkingHours and isOvertime and checkOut > overtimeThreshold:
                            extraTime = checkOut - idealCheckOutTime
                            overtime = extraTime.total_seconds() / 60
                            minOvertimeSalary = perDaySalary / 540
                            overtimeSalary = overtime * minOvertimeSalary
                        if attendanceDate.weekday() == 6:  
                            sundaysSalary += perDaySalary
                            sundays += 1
                        else:
                            fullDays += 1
                            totalSalary += perDaySalary
                    elif (idealWorkingHours * 0.88) <= totalWorkingHours < idealWorkingHours:
                        if attendanceDate.weekday() == 6:
                            sundaysSalary += 0.9 * perDaySalary
                            sundays += 1
                        else:
                            earlyCheckOutDays += 1
                            totalSalary += 0.9 * perDaySalary
                    elif (idealWorkingHours * 0.75) <= totalWorkingHours < (idealWorkingHours * 0.88):
                        if attendanceDate.weekday() == 6:
                            sundaysSalary += 0.75 * perDaySalary
                            sundays += 1
                        else:
                            threeFourQuarterDays += 1
                            totalSalary += 0.75 * perDaySalary
                    elif (idealWorkingHours * 0.5) <= totalWorkingHours < (idealWorkingHours * 0.75):
                        if attendanceDate.weekday() == 6:
                            sundaysSalary += 0.5 * perDaySalary
                            sundays += 1
                        else:
                            halfDays += 1
                            totalSalary += 0.5 * perDaySalary
                    elif (idealWorkingHours * 0.25) <= totalWorkingHours < (idealWorkingHours * 0.5):
                        if attendanceDate.weekday() == 6:
                            sundaysSalary += 0.25 * perDaySalary
                            sundays += 1
                        else:
                            quarterDays += 1
                            totalSalary += 0.25 * perDaySalary
                    elif totalWorkingHours < (idealWorkingHours * 0.25):
                            if attendanceDate.weekday() == 6:
                                sundaysSalary += 0.25 * perDaySalary
                                sundays += 1
                            else:
                               totalAbsents += 1
                   
                    if checkIn > idealCheckInTime and attendanceDate.weekday() != 6 and (idealWorkingHours * 0.88) <= totalWorkingHours < idealWorkingHours:
                        lates += 1
                        lateDeduction = 0.10 * perDaySalary
                        if lates > allowedLates:
                            # lates -= lates
                            totalLateDeductions = lates * lateDeduction
                    actualWorkingDays += 1
                else:
                    if any(holiday['holiday_date'] == today for holiday in holidays):
                        pass
                    else:
                        totalAbsents += 1
            else:
                if any(holiday['holiday_date'] == today for holiday in holidays):
                    pass
                else:
                    totalAbsents += 1
        
        totalSalary -= totalLateDeductions
        if actualWorkingDays > 0:
            totalSalary += (sundaysSalary + overtimeSalary + (len(holidays) * perDaySalary) + leaveEncashment)
        else:
            totalSalary += (sundaysSalary + overtimeSalary + leaveEncashment)
        
        data["salary_information"] = {
            "basic_salary": basicSalary,
            "per_day_salary": perDaySalary,
            "standard_working_days": totalWorkingDays,
            "actual_working_days": actualWorkingDays,
            "full_days": fullDays,
            "half_days": halfDays,
            "quarter_days": quarterDays,
            "three_four_quarter_days": threeFourQuarterDays,
            "sundays_working_days": sundays,
            "early_checkout_days": earlyCheckOutDays,
            "sundays_salary": sundaysSalary,
            "total_salary": round(totalSalary,2),
            "total_late_deductions": totalLateDeductions,
            "absent": totalAbsents,
            "lates": lates,
            "overtime": round((overtimeSalary),2),
            "holidays": round((len(holidays) * perDaySalary), 2),
            "leave_encashment": round((leaveEncashment),2)
        }
    
    return employeeData


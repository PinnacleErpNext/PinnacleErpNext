import frappe
from datetime import datetime, time

def calculate_monthly_salary(employeeData, totalWorkingDays, holidays, year, month):
    
    
    
    for emp_id, data in employeeData.items():
        basicSalary = data.get("basic_salary", 0)
        attendanceRecords = data.get("attendance_records", [])
        isOvertime = data.get("is_overtime")
        
        perDaySalary = round(basicSalary / totalWorkingDays, 2)
        
        shiftVariationRecord = frappe.db.sql("""
                                    SELECT svh.date AS attendance_date, svh.in_time, svh.out_time
                                    FROM `tabShift Variation` AS sv
                                    JOIN `tabShift Variation History` AS svh ON sv.name = svh.parent
                                    WHERE sv.year = %s AND sv.month_num = %s;
                                      """, (year, month), as_dict=True)
        
        shiftVariation = {
                            record['attendance_date']: record for record in shiftVariationRecord
                        }
        
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
        
        
        for day in range(1, totalWorkingDays + 1):
            today = datetime(year, month, day).date()
            
            attendanceRecord = next((record for record in attendanceRecords if record['attendance_date'] == today), None)
            
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
                    totalWorkingHours = totalWorkingTime.total_seconds() / 3600
                    
                    if (idealWorkingHours * 0.75) <= totalWorkingHours:
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
                    elif (idealWorkingHours * 0.50) <= totalWorkingHours < (idealWorkingHours * 0.75):
                        if attendanceDate.weekday() == 6:
                            sundaysSalary += 0.75 * perDaySalary
                            sundays += 1
                        else:
                            threeFourQuarterDays += 1
                            totalSalary += 0.75 * perDaySalary
                    elif (idealWorkingHours * 0.25) <= totalWorkingHours < (idealWorkingHours * 0.50):
                        if attendanceDate.weekday() == 6:
                            sundaysSalary += 0.5 * perDaySalary
                            sundays += 1
                        else:
                            halfDays += 1
                            totalSalary += 0.5 * perDaySalary
                    elif (idealWorkingHours * 0) <= totalWorkingHours < (idealWorkingHours * 0.25):
                        if attendanceDate.weekday() == 6:
                            sundaysSalary += 0.25 * perDaySalary
                            sundays += 1
                        else:
                            quarterDays += 1
                            totalSalary += 0.25 * perDaySalary
                   
                    if checkIn > idealCheckInTime and attendanceDate.weekday() != 6:
                        lates += 1
                        lateDeduction = 0.10 * perDaySalary
                        if lates > 6:
                            lates -= 6
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
            totalSalary += sundaysSalary + overtimeSalary + (len(holidays) * perDaySalary)
        else:
            totalSalary += sundaysSalary + overtimeSalary
        
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
            "sundays_salary": sundaysSalary,
            "total_salary": round(totalSalary, 2),
            "total_late_deductions": totalLateDeductions,
            "absent": totalAbsents,
            "lates": lates,
            "overtime": round((overtimeSalary),2),
            "holidays": round((len(holidays) * perDaySalary), 2)
        }
    
    return employeeData

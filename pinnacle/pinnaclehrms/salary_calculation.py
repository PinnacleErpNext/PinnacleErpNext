import frappe
from datetime import datetime, time

def calculate_monthly_salary(employee_data, total_working_days, holidays, year, month):
    
    
    
    for emp_id, data in employee_data.items():
        basic_salary = data.get("basic_salary", 0)
        attendance_records = data.get("attendance_records", [])
        
        per_day_salary = round(basic_salary / total_working_days, 2)
        
        
        total_salary = 0.0
        total_late_deductions = 0.0
        full_days = 0
        half_days = 0
        quarter_days = 0
        three_four_quarter_days = 0
        total_absents = 0
        lates = 0
        sundays = 0
        sundays_salary = 0.0
        overtime_salary = 0.0
        actual_working_days = 0
        
        
        for day in range(1, total_working_days + 1):
            today = datetime(year, month, day).date()
            
            attendance_record = next((record for record in attendance_records if record['attendance_date'] == today), None)
            
            if attendance_record:
                attendance_date = attendance_record["attendance_date"]
                in_time = attendance_record["in_time"]
                out_time = attendance_record["out_time"]
                shift = attendance_record["shift"]
                
                
                shift_start = frappe.db.get_value('Shift Type', {"name": shift}, "start_time")
                shift_end = frappe.db.get_value('Shift Type', {"name": shift}, "end_time")
                
                start_hours, remainder = divmod(shift_start.seconds, 3600)
                start_minutes, _ = divmod(remainder, 60)
                end_hours, remainder = divmod(shift_end.seconds, 3600)
                end_minutes, _ = divmod(remainder, 60)
                
                ideal_check_in_time = datetime.combine(attendance_date, time(start_hours, start_minutes))
                ideal_check_out_time = datetime.combine(attendance_date, time(end_hours, end_minutes))
                overtime_threshold = datetime.combine(attendance_date, time(19, 30))
                
                if in_time and out_time:
                    check_in = datetime.combine(attendance_date, in_time.time())
                    check_out = datetime.combine(attendance_date, out_time.time())
                    
                    total_working_time = check_out - check_in
                    total_working_hours = total_working_time.total_seconds() / 3600
                    
                    
                    if 7.875 <= total_working_hours <= 10.125:
                        overtime_salary = 0
                        if total_working_hours > 9 and check_out > overtime_threshold:
                            extra_time = check_out - ideal_check_out_time
                            overtime = extra_time.total_seconds() / 60
                            min_overtime_salary = per_day_salary / 540
                            overtime_salary = overtime * min_overtime_salary
                        
                        if attendance_date.weekday() == 6:  
                            sundays_salary += per_day_salary
                            sundays += 1
                        else:
                            full_days += 1
                            total_salary += per_day_salary
                    
                    elif 5.625 <= total_working_hours < 7.875:
                        if attendance_date.weekday() == 6:
                            sundays_salary += 0.75 * per_day_salary
                            sundays += 1
                        else:
                            three_four_quarter_days += 1
                            total_salary += 0.75 * per_day_salary
                    
                    elif 3.375 <= total_working_hours < 5.625:
                        if attendance_date.weekday() == 6:
                            sundays_salary += 0.5 * per_day_salary
                            sundays += 1
                        else:
                            half_days += 1
                            total_salary += 0.5 * per_day_salary
                    
                    elif 1.125 <= total_working_hours < 3.375:
                        if attendance_date.weekday() == 6:
                            sundays_salary += 0.25 * per_day_salary
                            sundays += 1
                        else:
                            quarter_days += 1
                            total_salary += 0.25 * per_day_salary
                    
                   
                    if check_in > ideal_check_in_time and attendance_date.weekday() != 6:
                        lates += 1
                        late_deduction = 0.10 * per_day_salary
                        if lates > 6:
                            lates -= 6
                            total_late_deductions = lates * late_deduction
                    actual_working_days += 1
                else:
                    if any(holiday['holiday_date'] == today for holiday in holidays):
                        pass
                    else:
                        total_absents += 1
            else:
                if any(holiday['holiday_date'] == today for holiday in holidays):
                    pass
                else:
                    total_absents += 1
        
        total_salary -= total_late_deductions
        if actual_working_days > 0:
            total_salary += sundays_salary + overtime_salary + (len(holidays) * per_day_salary)
        else:
            total_salary += sundays_salary + overtime_salary
        
        data["salary_information"] = {
            "basic_salary": basic_salary,
            "per_day_salary": per_day_salary,
            "standard_working_days": total_working_days,
            "actual_working_days": actual_working_days,
            "full_days": full_days,
            "half_days": half_days,
            "quarter_days": quarter_days,
            "three_four_quarter_days": three_four_quarter_days,
            "sundays_working_days": sundays,
            "sundays_salary": sundays_salary,
            "total_salary": round(total_salary, 2),
            "total_late_deductions": total_late_deductions,
            "absent": total_absents,
            "lates": lates,
            "overtime": round(overtime_salary, 2),
            "holidays": round((len(holidays) * per_day_salary), 2)
        }
    
    return employee_data

# Copyright (c) 2024, OTPL and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AssignSalary(Document):
	def before_save(self):
		# Add a new row to the salary_history child table
		new_row = self.append('salary_history', {})
		
		# Set values for the new row
		new_row.salary = self.new_salary
		new_row.from_date = self.from_date
  
	# def after_save(self):
	# 	frappe.db.set_value('Assign Salary', self.name, 'from_date', '')
	# 	frappe.db.set_value('Assign Salary', self.name, 'new_salary', '')

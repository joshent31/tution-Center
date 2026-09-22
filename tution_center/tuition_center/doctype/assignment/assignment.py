# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Assignment(Document):
    def validate(self):
        if self.due_date and self.assigned_date and self.due_date < self.assigned_date:
            frappe.throw("Due Date cannot be before Assigned Date")

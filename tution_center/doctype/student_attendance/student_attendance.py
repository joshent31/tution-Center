# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate


class StudentAttendance(Document):
    def validate(self):
        if not self.date:
            self.date = nowdate()

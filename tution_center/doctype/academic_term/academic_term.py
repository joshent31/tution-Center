# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


class AcademicTerm(Document):
    def validate(self):
        if self.term_end_date < self.term_start_date:
            frappe.throw(_("Term End Date cannot be before Term Start Date"))

        if self.status == "Active" and not (
            self.term_start_date <= today() <= self.term_end_date
        ):
            frappe.msgprint(_("Warning: today is outside the term dates"))

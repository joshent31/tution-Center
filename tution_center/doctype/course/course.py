# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class Course(Document):
    def validate(self):
        self.validate_assessment_weights()

    def validate_assessment_weights(self):
        total = sum(flt(row.weightage) for row in self.get("assessments", []))
        if total and total != 100:
            frappe.msgprint(
                _("Total assessment weightage should be 100%. Current: {0}%").format(total)
            )

    def update_enrolled_count(self):
        count = frappe.db.count(
            "Batch Student",
            filters={"course": self.name},
        )
        self.db_set("enrolled_students", count)

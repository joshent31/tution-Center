# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class ExamResult(Document):
    def validate(self):
        self.compute_percentage()
        self.compute_grade_and_result()

    def compute_percentage(self):
        if flt(self.max_marks) > 0:
            self.percentage = flt(self.marks_obtained) / flt(self.max_marks) * 100

    def compute_grade_and_result(self):
        pct = flt(self.percentage)
        if self.result != "Absent":
            self.result = "Pass" if pct >= 40 else "Fail"

        if pct >= 90:
            self.grade = "A+"
        elif pct >= 80:
            self.grade = "A"
        elif pct >= 70:
            self.grade = "B"
        elif pct >= 60:
            self.grade = "C"
        elif pct >= 50:
            self.grade = "D"
        elif pct >= 40:
            self.grade = "E"
        else:
            self.grade = "F"

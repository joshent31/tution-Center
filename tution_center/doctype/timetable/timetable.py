# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class Timetable(Document):
    def validate(self):
        if self.end_time and self.start_time and self.end_time <= self.start_time:
            frappe.throw(_("End time must be after start time"))

        if not self.day:
            from datetime import datetime

            self.day = getdate(self.timetable_date).strftime("%A")

        self.check_clashes()

    def check_clashes(self):
        rows = frappe.get_all(
            "Timetable",
            filters={
                "timetable_date": self.timetable_date,
                "name": ("!=", self.name),
                "status": ("!=", "Cancelled"),
            },
            fields=["name", "start_time", "end_time", "teacher", "batch"],
        )
        for r in rows:
            overlap = not (r.end_time <= self.start_time or r.start_time >= self.end_time)
            if not overlap:
                continue
            if self.teacher and r.teacher == self.teacher:
                frappe.throw(_("Teacher already has timetable {0} in this slot").format(r.name))
            if self.batch and r.batch == self.batch:
                frappe.throw(_("Batch already has timetable {0} in this slot").format(r.name))

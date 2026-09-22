# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, date_diff, flt, nowdate, today


class BookIssue(Document):
    def validate(self):
        if not self.due_date:
            self.due_date = add_days(self.issue_date or nowdate(), 14)

        if self.is_new() and self.status == "Issued":
            self.check_availability()

        if self.status == "Returned" and self.return_date:
            self.calculate_fine()

    def check_availability(self):
        book = frappe.get_doc("Book", self.book)
        if book.available_copies <= 0:
            frappe.throw(_("No copies of {0} available").format(book.book_name))
        book.available_copies -= 1
        book.save(ignore_permissions=True)

    def calculate_fine(self):
        if not self.due_date:
            return
        overdue = date_diff(self.return_date or today(), self.due_date)
        if overdue > 0:
            settings = frappe.get_cached_doc("Tuition Settings")
            self.fine = flt(overdue) * flt(settings.library_fine_per_day or 0)

    def on_update(self):
        self.sync_book_availability()

    def sync_book_availability(self):
        issued = frappe.db.count("Book Issue", {"book": self.book, "status": "Issued"})
        lost = frappe.db.count("Book Issue", {"book": self.book, "status": "Lost"})
        book = frappe.get_cached_doc("Book", self.book)
        available = flt(book.total_copies) - flt(issued) - flt(lost)
        frappe.db.set_value(
            "Book", self.book, "available_copies", max(available, 0), update_modified=False
        )

# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class Book(Document):
    def validate(self):
        if self.available_copies is None:
            self.available_copies = self.total_copies

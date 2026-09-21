# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class FeeStructure(Document):
    def validate(self):
        self.calculate_totals()

    def calculate_totals(self):
        total = 0
        discount = 0
        for row in self.get("components", []):
            amount = flt(row.amount)
            if flt(row.discount_percentage) > 0:
                row.discount_amount = amount * flt(row.discount_percentage) / 100
            net = amount - flt(row.discount_amount)
            row.net_amount = net
            total += amount
            discount += flt(row.discount_amount)

        self.total_amount = total
        self.total_discount = discount
        self.net_amount = total - discount

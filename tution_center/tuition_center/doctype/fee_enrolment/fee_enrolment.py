# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, today


class FeeEnrolment(Document):
    def validate(self):
        self.calculate_outstanding()

    def calculate_outstanding(self):
        self.outstanding_amount = flt(self.fee_amount) - flt(self.paid_amount)
        if flt(self.paid_amount) <= 0:
            self.status = "Unpaid"
        elif self.outstanding_amount <= 0:
            self.status = "Paid"
        else:
            self.status = "Partially Paid"

    def add_payment(
        self,
        amount,
        mode_of_payment=None,
        reference_no=None,
        payment_date=None,
    ):
        """Record a payment against this fee and update totals (supports part-payments)."""
        amount = flt(amount)
        if amount <= 0:
            frappe.throw(_("Payment amount must be greater than zero"))

        outstanding = flt(self.fee_amount) - flt(self.paid_amount)
        if amount > outstanding:
            frappe.throw(
                _("Payment {0} exceeds the outstanding balance {1}").format(
                    frappe.bold(amount), frappe.bold(outstanding)
                )
            )

        payment = frappe.get_doc(
            {
                "doctype": "Payment",
                "fee_enrolment": self.name,
                "student": self.student,
                "amount": amount,
                "mode_of_payment": mode_of_payment,
                "reference_no": reference_no,
                "payment_date": payment_date or today(),
            }
        )
        payment.insert(ignore_permissions=True)
        payment.submit()

        self.reload()
        return payment

    def update_paid_amount(self):
        """Recompute paid total from submitted payments."""
        total = frappe.db.sql(
            """select sum(amount) from `tabPayment`
               where fee_enrolment = %s and docstatus = 1""",
            (self.name,),
        )[0][0]
        self.db_set("paid_amount", flt(total))
        outstanding = flt(self.fee_amount) - flt(total or 0)
        self.db_set("outstanding_amount", outstanding)
        status = "Paid" if outstanding <= 0 else ("Partially Paid" if flt(total) > 0 else "Unpaid")
        self.db_set("status", status)

        # keep student's total dues fresh
        if self.student:
            student = frappe.get_doc("Student", self.student)
            student.update_stats()

    def on_update(self):
        self.sync_payment_rows(save=False)

    def sync_payment_rows(self, save=True):
        """Rebuild the payment-history child table from submitted payments.

        When ``save`` is set, the rebuilt rows are persisted to the database
        directly (bypassing full validate/save hooks to avoid recursion),
        so the displayed payment history is never stale.
        """
        payments = frappe.get_all(
            "Payment",
            filters={"fee_enrolment": self.name, "docstatus": 1},
            fields=["name", "amount", "mode_of_payment", "payment_date"],
            order_by="creation",
        )
        rows = [
            {
                "payment": p.name,
                "amount": p.amount,
                "mode_of_payment": p.mode_of_payment,
                "payment_date": p.payment_date,
            }
            for p in payments
        ]
        self.set("payments", rows)

        if save:
            self.flags.ignore_validate = True
            self.save(ignore_permissions=True)
            self.flags.ignore_validate = False

# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate


class Payment(Document):
    def validate(self):
        if not self.payment_date:
            self.payment_date = nowdate()
        if flt(self.amount) <= 0:
            frappe.throw(_("Payment amount must be greater than zero"))

        if self.fee_enrolment:
            enrolment = frappe.get_doc("Fee Enrolment", self.fee_enrolment)
            self.student = enrolment.student
            outstanding = flt(enrolment.fee_amount) - flt(enrolment.paid_amount)
            if flt(self.amount) > outstanding:
                frappe.throw(
                    _(
                        "Payment amount {0} exceeds the outstanding balance {1} for {2}. "
                        "Please record the exact amount due."
                    ).format(
                        frappe.bold(self.amount),
                        frappe.bold(outstanding),
                        frappe.bold(self.fee_enrolment),
                    )
                )

        self.validate_duplicate_reference()

    def validate_duplicate_reference(self):
        """Prevent the same payment reference being recorded twice."""
        if not self.reference_no:
            return
        filters = {
            "reference_no": self.reference_no,
            "docstatus": ("<", 2),
        }
        if self.fee_enrolment:
            filters["fee_enrolment"] = self.fee_enrolment
        if self.name:
            filters["name"] = ("!=", self.name)
        duplicate = frappe.db.get_value("Payment", filters, "name")
        if duplicate:
            frappe.throw(
                _("Payment reference {0} is already used in payment {1}").format(
                    frappe.bold(self.reference_no), frappe.bold(duplicate)
                ),
                frappe.DuplicateEntryError,
            )

    def before_insert(self):
        if not self.received_by:
            self.received_by = frappe.session.user

    def on_submit(self):
        self.update_enrolment()

    def on_cancel(self):
        self.update_enrolment()

    def update_enrolment(self):
        if self.fee_enrolment and frappe.db.exists("Fee Enrolment", self.fee_enrolment):
            enrolment = frappe.get_doc("Fee Enrolment", self.fee_enrolment)
            enrolment.update_paid_amount()
            enrolment.sync_payment_rows()
            frappe.db.commit()

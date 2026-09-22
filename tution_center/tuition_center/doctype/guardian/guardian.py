# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Guardian(Document):
    @frappe.whitelist()
    def create_portal_user(self):
        """Create a portal (Website User) account for this guardian and link it."""
        if self.user:
            frappe.msgprint(_("Guardian already linked to a user"))
            return self.user
        if not self.email:
            frappe.throw(_("Email required to create a portal user"))

        if frappe.db.exists("User", self.email):
            user = frappe.get_doc("User", self.email)
        else:
            user = frappe.get_doc(
                {
                    "doctype": "User",
                    "email": self.email,
                    "first_name": self.guardian_name,
                    "send_welcome_email": 0,
                    "user_type": "Website User",
                    "roles": [{"role": "Guardian"}],
                }
            ).insert(ignore_permissions=True)
        self.db_set("user", user.name)
        frappe.msgprint(_("Portal user {0} linked").format(frappe.bold(user.name)))
        return user.name

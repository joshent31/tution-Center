import frappe
from frappe.permissions import add_permission, update_permission_property


def after_install():
    make_roles()
    frappe.db.commit()


def before_uninstall():
    pass


def make_roles():
    """Create the three custom roles used by the app."""
    for role in ("Tuition Manager", "Tuition Teacher", "Guardian"):
        if not frappe.db.exists("Role", role):
            frappe.get_doc(
                {
                    "doctype": "Role",
                    "role_name": role,
                    "desk_access": 1 if role != "Guardian" else 0,
                }
            ).insert(ignore_permissions=True)

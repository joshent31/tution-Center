import frappe
from frappe.permissions import add_permission, update_permission_property


def after_install():
    make_module_def()
    make_roles()
    frappe.db.commit()


def make_module_def():
    """Ensure the Module Def exists (insurance for cached-out sites)."""
    if not frappe.db.exists("Module Def", "Tuition Center"):
        frappe.get_doc(
            {
                "doctype": "Module Def",
                "module_name": "Tuition Center",
                "app_name": "tution_center",
            }
        ).insert(ignore_permissions=True)


def before_uninstall():
    pass


def make_roles():
    """Create the roles used by the app (Student exists in ERPNext installs,
    but must be created when running on plain Frappe)."""
    for role in ("Tuition Manager", "Tuition Teacher", "Student", "Guardian"):
        if not frappe.db.exists("Role", role):
            frappe.get_doc(
                {
                    "doctype": "Role",
                    "role_name": role,
                    "desk_access": 1 if role not in ("Student", "Guardian") else 0,
                }
            ).insert(ignore_permissions=True)

import frappe
from frappe import _


def get_permission_query_conditions(user):
    """Restrict list views: teachers see batches they teach; students see their own docs."""
    if not user:
        return ""
    if "Tuition Manager" in frappe.get_roles(user):
        return ""
    if "System Manager" in frappe.get_roles(user):
        return ""

    conditions = []

    if "Tuition Teacher" in frappe.get_roles(user):
        teacher = frappe.db.get_value("Teacher", {"user": user}, "name")
        if teacher:
            conditions.append("`tabBatch`.teacher = {0}".format(frappe.db.escape(teacher)))

    return " or ".join(conditions) if conditions else "1=0"


def has_permission(doc, user):
    """Doc-level check used for Student, Fee Enrolment, Exam Result etc."""
    if not user:
        return False
    user_roles = frappe.get_roles(user)
    if "Tuition Manager" in user_roles or "System Manager" in user_roles:
        return True
    if "Tuition Teacher" in user_roles and getattr(doc, "owner", None) == user:
        return True
    if doc.doctype == "Student" and doc.get("user") == user:
        return True
    if doc.doctype == "Fee Enrolment":
        student = frappe.db.get_value("Student", {"user": user}, "name")
        if student and doc.student == student:
            return True
    return False

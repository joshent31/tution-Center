import frappe
from frappe import _

no_cache = 1


def get_context(context):
    """Server-rendered portal page: fees + announcements for logged-in user."""
    if frappe.session.user == "Guest":
        raise frappe.PermissionError(_("Please log in to view the portal"))

    user = frappe.session.user
    student = frappe.db.get_value("Student", {"user": user}, "name")

    if not student:
        guardian_students = frappe.get_all(
            "Guardian Student",
            filters={"parenttype": "Guardian", "user": user},
            pluck="student",
        )
        student_list = guardian_students
    else:
        student_list = [student]

    fees = []
    for s in student_list or []:
        rows = frappe.get_all(
            "Fee Enrolment",
            filters={"student": s},
            fields=[
                "name",
                "course",
                "academic_term",
                "fee_amount as fee",
                "paid_amount as paid",
                "status",
            ],
        )
        for r in rows:
            r.outstanding = (r.fee or 0) - (r.paid or 0)
            fees.append(r)

    announcements = frappe.get_all(
        "Announcement",
        filters={"publish_date": ("<=", frappe.utils.today())},
        fields=["title", "message", "publish_date", "type"],
        order_by="pinned desc, publish_date desc",
        limit_page_length=5,
    )

    context.fees = fees
    context.announcements = announcements
    context.centre_name = frappe.db.get_single_value("Tuition Settings", "centre_name")
    context.page_title = "My Tuition Portal"
    return context

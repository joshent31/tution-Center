# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt


def after_insert(doc, web_form):
    """Notify managers when a new admission application arrives."""
    import frappe

    managers = frappe.get_all(
        "Has Role",
        filters={"role": "Tuition Manager", "parenttype": "User"},
        pluck="parent",
        distinct=True,
    )
    if managers:
        frappe.sendmail(
            recipients=managers,
            subject=f"New Admission Application: {doc.student_name}",
            message=f"<p>A new admission application was received from <b>{doc.student_name}</b> ({doc.student_email_id}, {doc.student_mobile_number}).</p>",
        )

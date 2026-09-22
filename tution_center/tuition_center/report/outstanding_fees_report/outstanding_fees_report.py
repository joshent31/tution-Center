# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": _("Student"),
            "fieldname": "student",
            "fieldtype": "Link",
            "options": "Student",
            "width": 220,
        },
        {"label": _("Student Name"), "fieldname": "student_name", "width": 180},
        {"label": _("Course"), "fieldname": "course", "fieldtype": "Link", "options": "Course", "width": 140},
        {"label": _("Batch"), "fieldname": "batch", "fieldtype": "Link", "options": "Batch", "width": 140},
        {"label": _("Term"), "fieldname": "academic_term", "width": 120},
        {"label": _("Fee Amount"), "fieldname": "fee_amount", "fieldtype": "Currency", "width": 120},
        {"label": _("Paid"), "fieldname": "paid_amount", "fieldtype": "Currency", "width": 120},
        {
            "label": _("Outstanding"),
            "fieldname": "outstanding_amount",
            "fieldtype": "Currency",
            "width": 130,
        },
        {"label": _("Status"), "fieldname": "status", "width": 110},
        {"label": _("Due Date"), "fieldname": "due_date", "fieldtype": "Date", "width": 110},
    ]


def get_data(filters):
    conditions = ""
    values = {}

    if filters.get("student"):
        conditions += " and fe.student = %(student)s"
        values["student"] = filters.student

    if filters.get("course"):
        conditions += " and fe.course = %(course)s"
        values["course"] = filters.course

    if filters.get("batch"):
        conditions += " and fe.batch = %(batch)s"
        values["batch"] = filters.batch

    if filters.get("status"):
        conditions += " and fe.status = %(status)s"
        values["status"] = filters.status

    return frappe.db.sql(
        f"""
        select
            fe.student,
            fe.student_name,
            fe.course,
            fe.batch,
            fe.academic_term,
            fe.fee_amount,
            fe.paid_amount,
            fe.outstanding_amount,
            fe.status,
            fe.due_date
        from `tabFee Enrolment` fe
        where fe.docstatus < 2
        and fe.outstanding_amount > 0
        {conditions}
        order by fe.due_date asc
        """,
        values,
        as_dict=1,
    )

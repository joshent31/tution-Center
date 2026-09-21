# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
    columns, data = [], []
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": _("Payment"), "fieldname": "name", "fieldtype": "Link", "options": "Payment", "width": 150},
        {"label": _("Date"), "fieldname": "payment_date", "fieldtype": "Date", "width": 110},
        {
            "label": _("Student"),
            "fieldname": "student",
            "fieldtype": "Link",
            "options": "Student",
            "width": 200,
        },
        {"label": _("Student Name"), "fieldname": "student_name", "width": 180},
        {"label": _("Course"), "fieldname": "course", "fieldtype": "Link", "options": "Course", "width": 140},
        {"label": _("Mode"), "fieldname": "mode_of_payment", "width": 120},
        {"label": _("Amount"), "fieldname": "amount", "fieldtype": "Currency", "width": 130},
        {"label": _("Reference No"), "fieldname": "reference_no", "width": 140},
    ]


def get_data(filters):
    conditions = ""
    values = {}

    if filters.get("from_date"):
        conditions += " and p.payment_date >= %(from_date)s"
        values["from_date"] = filters.from_date

    if filters.get("to_date"):
        conditions += " and p.payment_date <= %(to_date)s"
        values["to_date"] = filters.to_date

    if filters.get("student"):
        conditions += " and p.student = %(student)s"
        values["student"] = filters.student

    return frappe.db.sql(
        f"""
        select
            p.name,
            p.payment_date,
            p.student,
            p.student_name,
            fe.course,
            p.mode_of_payment,
            p.amount,
            p.reference_no
        from `tabPayment` p
        left join `tabFee Enrolment` fe on fe.name = p.fee_enrolment
        where p.docstatus = 1
        {conditions}
        order by p.payment_date desc
        """,
        values,
        as_dict=1,
    )

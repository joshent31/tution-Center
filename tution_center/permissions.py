# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

"""Record-level permission helpers for the Tuition Center app.

Registered per DocType in hooks.py:

- ``permission_query_conditions`` — injects a SQL fragment into every
  list/report/query so users only see records inside their scope.
- ``has_permission`` — document-level scope check. Note: controller
  permission hooks can only DENY access; role-based DocType permissions
  still decide the base access. Returning ``None`` defers to role perms.

Scopes:
- System Manager / Tuition Manager: unrestricted (role permissions apply).
- Tuition Teacher: students, fees, payments, attendance and exams limited
  to the batches they teach; batches limited to their own.
- Student / Guardian: limited to their own (or their ward's) records.
- Everyone else: no access to protected records.
"""

import frappe

PROTECTED_DOCTYPES = (
    "Student",
    "Guardian",
    "Batch",
    "Fee Enrolment",
    "Payment",
    "Student Attendance",
    "Exam",
    "Exam Result",
)


# ------------------------------------------------------------------
# Identity helpers
# ------------------------------------------------------------------


def _is_manager(user):
    roles = frappe.get_roles(user)
    return "System Manager" in roles or "Tuition Manager" in roles


def _get_teacher(user):
    return frappe.db.get_value("Teacher", {"user": user}, "name")


def _get_own_students(user):
    """Student ids the user is linked to directly or as a guardian."""
    student = frappe.db.get_value("Student", {"user": user}, "name")
    if student:
        return [student]

    guardians = frappe.get_all("Guardian", filters={"user": user}, pluck="name")
    if not guardians:
        return []
    return list(
        set(
            frappe.get_all(
                "Guardian Student",
                filters={"parent": ("in", guardians), "parenttype": "Guardian"},
                pluck="student",
            )
        )
    )


def _get_teacher_batches(user):
    teacher = _get_teacher(user)
    if not teacher:
        return []
    return frappe.get_all("Batch", filters={"teacher": teacher}, pluck="name")


def _get_students_in_batches(batches):
    if not batches:
        return []
    return list(
        set(
            frappe.get_all(
                "Batch Student",
                filters={"parent": ("in", batches), "parenttype": "Batch", "active": 1},
                pluck="student",
            )
        )
    )


def _get_batches_of_students(students):
    if not students:
        return []
    return list(
        set(
            frappe.get_all(
                "Batch Student",
                filters={"student": ("in", students), "parenttype": "Batch", "active": 1},
                pluck="parent",
            )
        )
    )


def _sql_in(column, values):
    """SQL ``column in (...)`` fragment, or a never-true fragment when empty."""
    if not values:
        return "1=0"
    escaped = ", ".join(frappe.db.escape(v) for v in sorted(set(values)))
    return "{0} in ({1})".format(column, escaped)


def _scope_fragments(user, doctype):
    """List of SQL fragments restricting `doctype` rows for `user`."""
    column = "`tab{0}`.".format(doctype)
    fragments = []

    # Teacher scope: the batches they teach (and everything inside them)
    batches = _get_teacher_batches(user)
    if batches and doctype != "Guardian":
        if doctype == "Batch":
            fragments.append(_sql_in(column + "name", batches))
        elif doctype in ("Exam", "Exam Result"):
            fragments.append(_sql_in(column + "batch", batches))
        elif doctype == "Student":
            fragments.append(_sql_in(column + "name", _get_students_in_batches(batches)))
        else:
            # Fee Enrolment, Payment, Student Attendance carry a `student` link
            fragments.append(_sql_in(column + "student", _get_students_in_batches(batches)))
        if doctype == "Student Attendance":
            # attendance rows may be keyed by batch directly
            fragments.append(_sql_in(column + "batch", batches))

    # Student / guardian scope: their own (or their ward's) records
    students = _get_own_students(user)
    if students:
        if doctype == "Student":
            fragments.append(_sql_in(column + "name", students))
        elif doctype == "Batch":
            fragments.append(_sql_in(column + "name", _get_batches_of_students(students)))
        elif doctype in ("Exam", "Exam Result"):
            fragments.append(_sql_in(column + "batch", _get_batches_of_students(students)))
        elif doctype == "Guardian":
            fragments.append("{0}user = {1}".format(column, frappe.db.escape(user)))
        else:
            fragments.append(_sql_in(column + "student", students))

    return fragments


# ------------------------------------------------------------------
# Hook handlers (mapped per DocType in hooks.py)
# ------------------------------------------------------------------


def get_permission_query_conditions(user=None, doctype=None, **kwargs):
    """`permission_query_conditions` hook — scope list/report queries per DocType."""
    if not user:
        return "1=0"
    if user == "Administrator" or _is_manager(user):
        return ""
    fragments = _scope_fragments(user, doctype)
    return " or ".join(fragments) if fragments else "1=0"


def has_permission(doc=None, ptype=None, user=None, debug=False, **kwargs):
    """`has_permission` hook — document-level scope check.

    Returns True/False, or None to defer to role-based DocType permissions
    (controller hooks may only deny; they cannot grant access).
    """
    if doc is None:
        # doctype-level check (no document context) — let role perms decide
        return None
    if not user:
        user = frappe.session.user
    if user == "Administrator" or _is_manager(user):
        return None

    doctype = doc.doctype

    # Teachers: everything inside the batches they teach
    batches = _get_teacher_batches(user)
    if batches:
        if doctype == "Batch" and doc.name in batches:
            return True
        if doctype in ("Exam", "Exam Result") and doc.get("batch") in batches:
            return True
        batch_students = _get_students_in_batches(batches)
        if doctype == "Student" and doc.name in batch_students:
            return True
        if doctype == "Student Attendance" and doc.get("batch") in batches:
            return True
        if doctype in ("Fee Enrolment", "Payment", "Student Attendance") and (
            doc.get("student") in batch_students
        ):
            return True

    # Students / guardians: their own (or their ward's) records
    students = _get_own_students(user)
    if students:
        own_batches = _get_batches_of_students(students)
        if doctype == "Student" and doc.name in students:
            return True
        if doctype in ("Fee Enrolment", "Payment", "Student Attendance") and (
            doc.get("student") in students
        ):
            return True
        if doctype == "Batch" and doc.name in own_batches:
            return True
        if doctype in ("Exam", "Exam Result") and doc.get("batch") in own_batches:
            return True

    if doctype == "Guardian" and doc.get("user") == user:
        return True

    # Teachers keep owner-based read access (e.g. records they created)
    if ptype == "read" and (doc.get("owner") or "").lower() == (user or "").lower():
        return True

    return False

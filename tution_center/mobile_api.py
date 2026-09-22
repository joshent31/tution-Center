# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

"""Whitelisted API endpoints powering the mobile app (PWA at /mobile).

Every endpoint is scoped: students/guardians can only ever see data of
students linked to their user account; teachers only their own batches.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_datetime, nowdate, today

# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------


def _autolink_by_email(doctype, user):
    """Link a Student/Teacher record whose email matches the login email.

    Covers the common case where the Student/Teacher record was created
    (with an email) before or after the portal user account, so nobody has
    to open the record and set the `user` field by hand.
    """
    email = (frappe.db.get_value("User", user, "email") or user or "").strip()
    if not email or "@" not in email:
        return None
    email_field = "student_email_id" if doctype == "Student" else "email"
    name = frappe.db.get_value(doctype, {email_field: email}, "name")
    # only claim records not already linked to another account
    if not name or frappe.db.get_value(doctype, name, "user"):
        return None
    frappe.db.set_value(doctype, name, "user", user, update_modified=False)
    return name


def _autolink_guardians_by_email(user):
    """Link Guardian records matching the login email (family-shared accounts)."""
    email = (frappe.db.get_value("User", user, "email") or user or "").strip()
    if not email or "@" not in email:
        return []
    rows = frappe.get_all(
        "Guardian", filters={"email": email, "user": ("is", "not set")}, pluck="name"
    )
    for name in rows:
        frappe.db.set_value("Guardian", name, "user", user, update_modified=False)
    return rows


def _get_students_for_user(user=None):
    """Student ids for the logged-in user: self, or all children of a guardian.

    Auto-links profiles by email on first use, so a login whose Student /
    Guardian record exists but has no `user` set still resolves.
    """
    user = user or frappe.session.user

    student = frappe.db.get_value("Student", {"user": user}, "name")
    if not student:
        student = _autolink_by_email("Student", user)
    if student:
        return [student]

    guardians = frappe.get_all("Guardian", filters={"user": user}, pluck="name")
    if not guardians:
        guardians = _autolink_guardians_by_email(user)
    if not guardians:
        return []
    return frappe.get_all(
        "Guardian Student",
        filters={"parent": ("in", guardians), "parenttype": "Guardian"},
        pluck="student",
    )


def _is_teacher(user=None):
    user = user or frappe.session.user
    teacher = frappe.db.get_value("Teacher", {"user": user}, "name")
    if not teacher:
        teacher = _autolink_by_email("Teacher", user)
    return teacher


def _get_students_for_request():
    """Students the current user is allowed to query (or ?student= override)."""
    user = frappe.session.user
    allowed = _get_students_for_user(user)
    teacher = _is_teacher(user)
    if teacher or "Tuition Manager" in frappe.get_roles(user):
        return allowed, teacher
    requested = frappe.form_dict.get("student")
    if requested and requested not in allowed:
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    return allowed, teacher


def _require_login():
    if frappe.session.user == "Guest":
        frappe.throw(_("Please log in"), frappe.PermissionError)


def _currency():
    return frappe.db.get_single_value("Tuition Settings", "default_currency") or "INR"


def _resolve_batch(batch):
    """Resolve a student/teacher to their batch (validation + default)."""
    allowed_students, teacher = _get_students_for_request()
    if "Tuition Manager" in frappe.get_roles(frappe.session.user):
        return batch
    if teacher:
        if batch:
            b = frappe.db.get_value("Batch", batch, "teacher", as_dict=True)
            if b and b.teacher != teacher:
                frappe.throw(_("Not permitted"), frappe.PermissionError)
            return batch
        return frappe.db.get_value("Batch", {"teacher": teacher}, "name")

    if batch:
        if batch not in frappe.get_all(
            "Batch Student",
            filters={"student": ("in", allowed_students), "parenttype": "Batch"},
            pluck="parent",
        ):
            frappe.throw(_("Not permitted"), frappe.PermissionError)
        return batch
    if allowed_students:
        return frappe.db.get_value(
            "Batch Student",
            {"student": ("in", allowed_students), "parenttype": "Batch", "active": 1},
            "parent",
        )
    return None


# ------------------------------------------------------------------
# hooks helpers (website user home page, portal context)
# ------------------------------------------------------------------


def get_website_user_home_page(user):
    """Send students/guardians/teachers to the mobile app after login."""
    return "/mobile"


def update_website_context(context):
    """Point the website 'Login' redirect at the mobile app."""
    context.update({"login_with": "/mobile"})


# ------------------------------------------------------------------
# hooks helpers end
# ------------------------------------------------------------------


# ------------------------------------------------------------------
# 1. bootstrap
# ------------------------------------------------------------------


@frappe.whitelist()
def get_me():
    """Everything the app needs right after login: profile + switcher + counts."""
    _require_login()
    user = frappe.session.user
    roles = frappe.get_roles(user)
    allowed_students, teacher = _get_students_for_request()
    currency = _currency()

    centre = frappe.db.get_single_value("Tuition Settings", "centre_name") or "Josh Tuition Centre"

    is_manager = "Tuition Manager" in roles or "System Manager" in roles

    if not allowed_students and not teacher:
        if is_manager:
            # Managers get the centre dashboard — no personal profile needed.
            return {
                "user": user,
                "fullname": frappe.db.get_value("User", user, "full_name"),
                "roles": roles,
                "centre": centre,
                "currency": currency,
                "is_teacher": False,
                "is_manager": True,
                "teacher_id": None,
                "students": [],
                "default_student": None,
                "summary": _manager_summary(),
            }
        if frappe.db.exists("Guardian", {"user": user}):
            frappe.throw(
                _(
                    "Your guardian profile has no students linked yet. Ask the centre "
                    "office to add you in the student's Guardians table."
                ),
                frappe.PermissionError,
            )
        frappe.throw(
            _(
                "No Student, Guardian or Teacher record is linked to your account ({0}) yet. "
                "Ask the centre office to open your record and click 'Create Portal User', "
                "or set its 'User' field to {0}. Records whose email matches your login "
                "are linked automatically the next time you sign in."
            ).format(frappe.bold(user)),
            frappe.PermissionError,
        )

    def profile(doctype, name):
        if doctype == "Student":
            label_field = "student_name"
        else:
            label_field = "teacher_name"
        d = frappe.db.get_value(doctype, name, [label_field, "photo", "status"], as_dict=True)
        return {
            "id": name,
            "name": d.get(label_field),
            "photo": d.photo or "",
            "status": d.status,
            "type": doctype,
        }

    profiles = []
    for s in allowed_students:
        profiles.append(profile("Student", s))
    if teacher:
        profiles.append(profile("Teacher", teacher))

    default = profiles[0]
    summary = get_student_summary(student_id=default["id"], _internal=True) if default["type"] == "Student" else {}
    if summary:
        summary["currency"] = currency

    return {
        "user": user,
        "fullname": frappe.db.get_value("User", user, "full_name"),
        "roles": roles,
        "centre": centre,
        "currency": currency,
        "is_teacher": bool(teacher),
        "is_manager": is_manager,
        "teacher_id": teacher,
        "students": profiles,
        "default_student": default["id"],
        "summary": summary,
    }


# ------------------------------------------------------------------
# 2. dashboard / summary
# ------------------------------------------------------------------


@frappe.whitelist()
def get_student_summary(student_id=None, _internal=False):
    """One round-trip dashboard payload for a student (or teacher's batch view)."""
    if not _internal:
        _require_login()
        allowed_students, teacher = _get_students_for_request()
        if not teacher and not allowed_students and "Tuition Manager" in frappe.get_roles():
            return {}  # pure manager: no personal student view
        if teacher and not student_id:
            return _teacher_summary(teacher)
        if not student_id:
            student_id = allowed_students[0] if allowed_students else None
        if student_id not in allowed_students:
            frappe.throw(_("Not permitted"), frappe.PermissionError)
    elif frappe.session.user == "Guest":
        frappe.throw(_("Please log in"), frappe.PermissionError)

    if not student_id:
        return {}

    student = frappe.db.get_value(
        "Student",
        student_id,
        ["name", "student_name", "photo", "status", "grade_level", "school", "total_fees_due"],
        as_dict=True,
    )

    batches = frappe.get_all(
        "Batch Student",
        filters={"student": student_id, "parenttype": "Batch", "active": 1},
        pluck="parent",
    )
    batch_info = frappe.get_all(
        "Batch",
        filters={"name": ("in", batches)},
        fields=["name", "batch_name", "course", "teacher", "status"],
    )

    dues = frappe.db.sql(
        """select ifnull(sum(fee_amount - paid_amount), 0) from `tabFee Enrolment`
           where student = %s and status in ('Unpaid', 'Partially Paid') and docstatus < 2""",
        (student_id,),
    )[0][0]

    attendance_total = frappe.db.count("Student Attendance", {"student": student_id})
    attendance_present = frappe.db.count(
        "Student Attendance", {"student": student_id, "status": "Present"}
    )
    attendance_pct = (attendance_present / attendance_total * 100) if attendance_total else 0

    today_classes = _today_classes_for_batches(batches)

    # outstanding-per-month sparkline (last 6 months of payments)
    monthly = frappe.db.sql(
        """select date_format(payment_date, '%%Y-%%m') ym, sum(amount) total
           from `tabPayment`
           where student = %s and docstatus = 1
           group by ym order by ym desc limit 6""",
        (student_id,),
        as_dict=True,
    )

    return {
        "student": student,
        "batches": batch_info,
        "outstanding": flt(dues),
        "attendance_pct": round(attendance_pct, 1),
        "attendance_marked": attendance_total,
        "today_classes": today_classes,
        "recent_payments": monthly,
    }


def _teacher_summary(teacher):
    """Teacher dashboard: batches, student counts, today's slots."""
    batches = frappe.get_all(
        "Batch",
        filters={"teacher": teacher},
        fields=["name", "batch_name", "course", "status", "max_seats"],
    )
    for b in batches:
        b.student_count = frappe.db.count(
            "Batch Student", {"parent": b.name, "parenttype": "Batch", "active": 1}
        )
    slots = _today_classes_for_batches([b.name for b in batches])
    return {
        "teacher": frappe.db.get_value(
            "Teacher", teacher, ["name", "teacher_name", "photo"], as_dict=True
        ),
        "batches": batches,
        "today_classes": slots,
        "total_students": sum(b.student_count for b in batches),
    }


def _today_classes_for_batches(batches):
    weekday = get_datetime(today()).strftime("%A")
    slots = frappe.get_all(
        "Timetable Slot",
        filters={"parent": ("in", batches), "parenttype": "Batch", "day": weekday},
        fields=["day", "start_time", "end_time", "course", "teacher", "room", "parent as batch"],
        order_by="start_time",
    )
    return {"day": weekday, "slots": slots}


# ------------------------------------------------------------------
# 3. profile
# ------------------------------------------------------------------


@frappe.whitelist()
def get_student_profile(student_id=None):
    """Full profile incl. batches, guardians, contact (scoped)."""
    _require_login()
    allowed_students, _teacher = _get_students_for_request()
    if not student_id:
        student_id = allowed_students[0] if allowed_students else None
    if student_id not in allowed_students:
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    student = frappe.get_doc("Student", student_id)
    guardians = [
        {
            "name": g.guardian,
            "guardian_name": g.guardian_name,
            "relationship": g.relationship,
        }
        for g in student.get("guardians", [])
    ]
    batches = frappe.get_all(
        "Batch Student",
        filters={"student": student_id, "parenttype": "Batch"},
        fields=["parent as batch", "active"],
    )
    return {
        "student": student.as_dict(),
        "guardians": guardians,
        "batches": batches,
    }


@frappe.whitelist()
def update_student_photo(student_id, photo):
    """Students/guardians can update their own profile picture from the app."""
    _require_login()
    allowed_students, _teacher = _get_students_for_request()
    if student_id not in allowed_students:
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    frappe.db.set_value("Student", student_id, "photo", photo)
    return {"ok": 1, "photo": photo}


# ------------------------------------------------------------------
# 4. fees
# ------------------------------------------------------------------


@frappe.whitelist()
def get_fees(student_id=None):
    """Fee ledger: enrolments + payments + computed totals (scoped)."""
    _require_login()
    allowed_students, _teacher = _get_students_for_request()
    if not student_id:
        student_id = allowed_students[0] if allowed_students else None
    if student_id not in allowed_students:
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    enrolments = frappe.get_all(
        "Fee Enrolment",
        filters={"student": student_id},
        fields=[
            "name", "course", "batch", "academic_term", "fee_amount",
            "paid_amount", "outstanding_amount", "status", "due_date",
        ],
        order_by="due_date asc",
    )
    payments = frappe.get_all(
        "Payment",
        filters={"student": student_id, "docstatus": 1},
        fields=["name", "fee_enrolment", "amount", "mode_of_payment", "payment_date", "reference_no"],
        order_by="payment_date desc",
        limit_page_length=50,
    )
    totals = {"fee": 0, "paid": 0, "outstanding": 0}
    for e in enrolments:
        totals["fee"] += flt(e.fee_amount)
        totals["paid"] += flt(e.paid_amount)
        totals["outstanding"] += flt(e.outstanding_amount)
    return {
        "enrolments": enrolments,
        "payments": payments,
        "totals": totals,
        "currency": _currency(),
    }


# ------------------------------------------------------------------
# 5. timetable
# ------------------------------------------------------------------


@frappe.whitelist()
def get_timetable(batch=None):
    """Weekly timetable for the caller's (or requested) batch, scoped."""
    _require_login()
    batch = _resolve_batch(batch)
    if not batch and "Tuition Manager" in frappe.get_roles(frappe.session.user):
        # managers have no personal batch — show the first active one
        batch = frappe.db.get_value("Batch", {"status": "Active"}, "name")
    if not batch:
        return {"slots": [], "batch": None}

    slots = frappe.get_all(
        "Timetable Slot",
        filters={"parent": batch, "parenttype": "Batch"},
        fields=["day", "start_time", "end_time", "course", "teacher", "room"],
        order_by="field(day,'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'), start_time",
    )
    batch_name = frappe.db.get_value("Batch", batch, "batch_name")
    return {"batch": batch, "batch_name": batch_name, "slots": slots}


# ------------------------------------------------------------------
# 6. results & attendance
# ------------------------------------------------------------------


@frappe.whitelist()
def get_results(student_id=None):
    """Published exam results for a student (scoped)."""
    _require_login()
    allowed_students, _teacher = _get_students_for_request()
    if not student_id:
        if not allowed_students and "Tuition Manager" in frappe.get_roles():
            return {"results": [], "stats": {"pass": 0, "fail": 0, "avg_pct": 0}}
        student_id = allowed_students[0] if allowed_students else None
    if student_id not in allowed_students:
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    results = frappe.get_all(
        "Exam Result",
        filters={"student": student_id, "docstatus": ("<", 2)},
        fields=[
            "name", "exam", "course", "batch", "exam_date", "max_marks",
            "marks_obtained", "percentage", "grade", "result", "remarks",
        ],
        order_by="exam_date desc",
        limit_page_length=100,
    )
    stats = {"pass": 0, "fail": 0, "avg_pct": 0}
    pcts = [r.percentage for r in results if r.percentage is not None]
    if pcts:
        stats["avg_pct"] = round(sum(pcts) / len(pcts), 1)
    stats["pass"] = len([r for r in results if r.result == "Pass"])
    stats["fail"] = len([r for r in results if r.result == "Fail"])
    return {"results": results, "stats": stats}


@frappe.whitelist()
def get_attendance(student_id=None, from_date=None, to_date=None):
    """Attendance history + monthly percentage (scoped)."""
    _require_login()
    allowed_students, _teacher = _get_students_for_request()
    if not student_id:
        if not allowed_students and "Tuition Manager" in frappe.get_roles():
            return {
                "from_date": from_date or add_days(today(), -90),
                "to_date": to_date or today(),
                "records": [], "percentage": 0, "total": 0, "present": 0,
                "absent": 0, "leave": 0,
            }
        student_id = allowed_students[0] if allowed_students else None
    if student_id not in allowed_students:
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    from_date = from_date or add_days(today(), -90)
    to_date = to_date or today()
    rows = frappe.get_all(
        "Student Attendance",
        filters={"student": student_id, "date": ("between", [from_date, to_date])},
        fields=["date", "status", "batch"],
        order_by="date desc",
    )
    total = len(rows)
    present = len([r for r in rows if r.status == "Present"])
    return {
        "from_date": from_date,
        "to_date": to_date,
        "records": rows,
        "percentage": round(present / total * 100, 1) if total else 0,
        "total": total,
        "present": present,
        "absent": len([r for r in rows if r.status == "Absent"]),
        "leave": len([r for r in rows if r.status == "Leave"]),
    }


# ------------------------------------------------------------------
# 7. teacher tools
# ------------------------------------------------------------------


@frappe.whitelist()
def get_batch_students(batch):
    """Roster for the Attendance screen (teachers only)."""
    _require_login()
    teacher = _is_teacher()
    if not teacher and "Tuition Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw(_("Only teachers can view batch rosters"), frappe.PermissionError)
    batch = _resolve_batch(batch)
    return frappe.get_all(
        "Batch Student",
        filters={"parent": batch, "parenttype": "Batch", "active": 1},
        fields=["student", "student_name"],
        order_by="idx",
    )


@frappe.whitelist()
def mark_attendance(students, date, batch, status_map):
    """Bulk attendance from the mobile app (teachers only)."""
    _require_login()
    teacher = _is_teacher()
    if not teacher and "Tuition Manager" not in frappe.get_roles(frappe.session.user):
        frappe.throw(_("Only teachers can mark attendance"), frappe.PermissionError)

    if isinstance(students, str):
        students = json.loads(students)
    if isinstance(status_map, str):
        status_map = json.loads(status_map)

    batch = _resolve_batch(batch)

    from tution_center.api import mark_attendance as _core_mark

    return _core_mark(students, date, batch, status_map)


@frappe.whitelist()
def get_assignments(student_id=None):
    """Assignments for the student's batches with submission status (scoped)."""
    _require_login()
    allowed_students, _teacher = _get_students_for_request()
    if not student_id:
        if not allowed_students and "Tuition Manager" in frappe.get_roles():
            return {"assignments": []}
        student_id = allowed_students[0] if allowed_students else None
    if student_id not in allowed_students:
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    batches = frappe.get_all(
        "Batch Student",
        filters={"student": student_id, "parenttype": "Batch", "active": 1},
        pluck="parent",
    )
    assignments = frappe.get_all(
        "Assignment",
        filters={"batch": ("in", batches or [""])},
        fields=["name", "title", "course", "batch", "assigned_date", "due_date", "max_score", "status"],
        order_by="due_date desc",
        limit_page_length=50,
    )
    submissions = frappe.get_all(
        "Assignment Submission",
        filters={"parent": ("in", [a.name for a in assignments] or [""]), "student": student_id},
        fields=["parent as assignment", "student", "submission_date", "score", "status"],
    )
    sub_map = {s.assignment: s for s in submissions}
    for a in assignments:
        a.my_submission = sub_map.get(a.name)
    return {"assignments": assignments}


# ------------------------------------------------------------------
# 8. complaints (from the app)
# ------------------------------------------------------------------


@frappe.whitelist()
def create_complaint(subject, type="Other", description=None, student=None):
    """Raise a complaint as the logged-in user (optionally linked to a student)."""
    _require_login()
    allowed_students, _teacher = _get_students_for_request()
    if student and student not in allowed_students:
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    user = frappe.session.user
    complainant = frappe.db.get_value("User", user, "full_name") or user

    doc = frappe.get_doc(
        {
            "doctype": "Complaint",
            "raised_by": user,
            "complainant_name": complainant,
            "complaint_type": type,
            "priority": "Medium",
            "status": "Open",
            "student": student or None,
            "subject": subject,
            "description": description,
        }
    )
    doc.insert(ignore_permissions=True)
    return {"name": doc.name, "due_date": doc.due_date}


# ------------------------------------------------------------------
# 9. announcements
# ------------------------------------------------------------------


@frappe.whitelist()
def get_announcements():
    """Active announcements for the app home screen."""
    _require_login()
    return frappe.get_all(
        "Announcement",
        filters={"publish_date": ("<=", today())},
        or_filters=[["expiry_date", ">=", today()], ["expiry_date", "is", "not set"]],
        fields=["title", "message", "publish_date", "expiry_date", "type", "pinned"],
        order_by="pinned desc, publish_date desc",
        limit_page_length=10,
    )


# ------------------------------------------------------------------
# 9. push notification registration (future FCM / WhatsApp hooks)
# ------------------------------------------------------------------


@frappe.whitelist()
def register_push_token(token, platform="web"):
    """Register the device push token (logged now; wired to FCM in the roadmap)."""
    _require_login()
    allowed_students, teacher = _get_students_for_request()
    if not allowed_students and not teacher:
        frappe.throw(_("No profile linked to your account"))
    frappe.logger("tuition_push").info(
        f"push token registered: user={frappe.session.user} platform={platform}"
    )
    return {"ok": 1}


# ------------------------------------------------------------------
# 10. manager dashboard
# ------------------------------------------------------------------


def _manager_summary():
    """Centre-wide aggregates for the mobile manager dashboard."""
    def scalar(sql, values=None):
        row = frappe.db.sql(sql, values)
        return float(row[0][0] or 0) if row else 0.0

    fees_expected = scalar(
        "select coalesce(sum(fee_amount), 0) from `tabFee Enrolment` where docstatus < 2"
    )
    fees_collected = scalar(
        "select coalesce(sum(amount), 0) from `tabPayment` where docstatus = 1"
    )

    students_active = frappe.db.count("Student", {"status": "Active"})
    batches_active = frappe.db.count("Batch", {"status": "Active"})
    teachers = frappe.db.count("Teacher", {"status": "Active"})
    complaints_open = frappe.db.count("Complaint", {"status": "Open"})

    upcoming_exams = frappe.get_all(
        "Exam",
        filters={"exam_date": (">=", today()), "docstatus": ("<", 2)},
        fields=["name", "exam_name", "exam_date", "course", "room"],
        order_by="exam_date asc",
        limit_page_length=5,
    )
    recent_payments = frappe.get_all(
        "Payment",
        filters={"docstatus": 1},
        fields=["name", "student", "student_name", "payment_date", "amount", "mode_of_payment"],
        order_by="payment_date desc, creation desc",
        limit_page_length=5,
    )
    complaints = frappe.get_all(
        "Complaint",
        filters={"status": ("in", ["Open", "In Progress"])},
        fields=["name", "subject", "status", "creation"],
        order_by="creation desc",
        limit_page_length=5,
    )

    return {
        "students_active": students_active,
        "batches_active": batches_active,
        "teachers": teachers,
        "complaints_open": complaints_open,
        "fees_expected": fees_expected,
        "fees_collected": fees_collected,
        "fees_outstanding": max(fees_expected - fees_collected, 0),
        "upcoming_exams": upcoming_exams,
        "recent_payments": recent_payments,
        "complaints": complaints,
    }

import frappe
from frappe import _
from frappe.utils import (
    add_days,
    flt,
    now_datetime,
    today,
)

# ------------------------------------------------------------------


def extend_bootinfo(bootinfo):
    """Expose tuition settings in desk boot."""
    bootinfo.tuition_settings = frappe.get_cached_doc("Tuition Settings")


# ------------------------------------------------------------------
# Attendance
# ------------------------------------------------------------------


@frappe.whitelist()
def get_batch_students(batch):
    """Students enrolled in a batch — used by Attendance Tool."""
    if not frappe.has_permission("Student", "read"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)
    return frappe.get_all(
        "Batch Student",
        filters={"parent": batch, "parenttype": "Batch"},
        fields=["student", "student_name"],
        order_by="idx",
    )


@frappe.whitelist()
def mark_attendance(students, date, batch, status_map):
    """Bulk-mark attendance.

    students: list of student ids; status_map: {"Present": [...], "Absent": [...]}
    """
    import json

    if isinstance(students, str):
        students = json.loads(students)
    if isinstance(status_map, str):
        status_map = json.loads(status_map)

    if not frappe.has_permission("Student Attendance", "create"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    created = 0
    for student in students:
        status = "Present"
        if student in status_map.get("Absent", []):
            status = "Absent"
        elif student in status_map.get("Leave", []):
            status = "Leave"

        existing = frappe.db.exists(
            "Student Attendance",
            {"student": student, "date": date, "batch": batch, "docstatus": 1},
        )
        if existing:
            frappe.db.set_value("Student Attendance", existing, "status", status)
        else:
            frappe.get_doc(
                {
                    "doctype": "Student Attendance",
                    "student": student,
                    "date": date,
                    "batch": batch,
                    "status": status,
                }
            ).insert(ignore_permissions=True)
            created += 1

    return {"created": created, "date": date, "batch": batch}


# ------------------------------------------------------------------
# Fee reminders
# ------------------------------------------------------------------


@frappe.whitelist()
def send_fee_reminder(fee_enrolment):
    """Send an immediate reminder for one Fee Enrolment."""
    if not frappe.has_permission("Fee Enrolment", "write"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    doc = frappe.get_doc("Fee Enrolment", fee_enrolment)
    if not doc.student:
        frappe.throw(_("No student linked"))

    student = frappe.get_doc("Student", doc.student)
    outstanding = flt(doc.fee_amount) - flt(doc.paid_amount)

    if outstanding <= 0:
        frappe.msgprint(_("No outstanding amount"))
        return

    send_reminder_email(student, doc, outstanding)
    frappe.msgprint(_("Reminder sent to {0}").format(student.student_name))


def send_reminder_email(student, enrolment, outstanding):
    currency = frappe.db.get_single_value("Tuition Settings", "default_currency") or "INR"
    subject = _("Fee Payment Reminder - {0}").format(student.student_name)
    message = f"""
    <p>Dear {student.student_name},</p>
    <p>This is a reminder that an outstanding amount of
    <b>{frappe.utils.fmt_money(outstanding, currency=currency)}</b>
    is due for {enrolment.course or "your course"} ({enrolment.academic_term or ""}).</p>
    <p>Please pay at your earliest convenience.</p>
    <p>Regards,<br>Tuition Center</p>
    """
    frappe.sendmail(
        recipients=[student.student_email_id] if student.student_email_id else [],
        subject=subject,
        message=message,
        reference_doctype="Fee Enrolment",
        reference_name=enrolment.name,
    )


def send_fee_reminders():
    """Daily scheduled job — remind all unpaid/partially paid fee enrolments."""
    settings = frappe.get_cached_doc("Tuition Settings")
    if not settings.enable_fee_reminders:
        return

    enrolments = frappe.get_all(
        "Fee Enrolment",
        filters={"status": ("in", ["Unpaid", "Partially Paid"])},
        fields=["name", "student", "fee_amount", "paid_amount", "course", "academic_term"],
    )

    sent = 0
    for e in enrolments:
        outstanding = flt(e.fee_amount) - flt(e.paid_amount)
        if outstanding <= 0:
            continue
        student = frappe.get_cached_value(
            "Student", e.student, ["student_name", "student_email_id"], as_dict=True
        )
        if not student or not student.student_email_id:
            continue
        send_reminder_email(
            frappe._dict(
                student_name=student.student_name, student_email_id=student.student_email_id
            ),
            e,
            outstanding,
        )
        sent += 1

    frappe.logger("tuition").info(f"Fee reminders sent: {sent}")


# ------------------------------------------------------------------
# SMS
# ------------------------------------------------------------------


@frappe.whitelist()
def send_sms_to_students(students, message):
    """Send SMS to selected students' mobile numbers via frappe sms."""
    import json

    if isinstance(students, str):
        students = json.loads(students)

    if not frappe.has_permission("Student", "read"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    numbers = []
    for name in students:
        mobile = frappe.db.get_value("Student", name, "student_mobile_number")
        if mobile:
            numbers.append(mobile)

    if not numbers:
        frappe.msgprint(_("No mobile numbers found"))
        return

    from frappe.core.doctype.sms_settings.sms_settings import send_sms

    send_sms(numbers, message)
    frappe.msgprint(_("SMS queued to {0} recipients").format(len(numbers)))


# ------------------------------------------------------------------
# Timetable / portal
# ------------------------------------------------------------------


@frappe.whitelist()
def get_student_timetable(batch, date=None):
    """Timetable slots for a batch, used by portal & desk."""
    slots = frappe.get_all(
        "Timetable Slot",
        filters={"parent": batch, "parenttype": "Batch"},
        fields=["day", "start_time", "end_time", "course", "teacher", "room"],
        order_by="day, start_time",
    )
    return slots


def _get_students_for_user(user):
    """Resolve the logged-in user's student ids (self or as guardian)."""
    student = frappe.db.get_value("Student", {"user": user}, "name")
    if student:
        return [student]

    guardians = frappe.get_all("Guardian", filters={"user": user}, pluck="name")
    if not guardians:
        return []
    return frappe.get_all(
        "Guardian Student",
        filters={"parent": ("in", guardians), "parenttype": "Guardian"},
        pluck="student",
    )


@frappe.whitelist()
def get_portal_fees():
    """Fee data for the logged-in student / guardian portal."""
    user = frappe.session.user
    student_list = _get_students_for_user(user)
    if not student_list:
        frappe.throw(_("No student linked to your account"), frappe.PermissionError)

    out = []
    for s in student_list:
        fees = frappe.get_all(
            "Fee Enrolment",
            filters={"student": s},
            fields=[
                "name",
                "course",
                "academic_term",
                "fee_amount",
                "paid_amount",
                "status",
                "due_date",
            ],
        )
        out.extend(fees)
    return out


@frappe.whitelist()
def get_student_dashboard_data():
    """Counts for portal homepage."""
    user = frappe.session.user
    student_list = _get_students_for_user(user)
    if not student_list:
        return {}

    outstanding = frappe.db.sql(
        """select sum(fee_amount - paid_amount) from `tabFee Enrolment`
           where student in %s and status in ('Unpaid','Partially Paid')""",
        (tuple(student_list),),
    )[0][0]

    return {
        "students": student_list,
        "outstanding": outstanding or 0,
    }


# ------------------------------------------------------------------
# Digests
# ------------------------------------------------------------------


def send_weekly_digest():
    """Weekly summary email to Tuition Managers."""
    managers = frappe.get_all(
        "Has Role",
        filters={"role": "Tuition Manager", "parenttype": "User"},
        pluck="parent",
        distinct=True,
    )
    if not managers:
        return

    week_ago = add_days(today(), -7)
    stats = {
        "new_students": frappe.db.count("Student", {"creation": (">", week_ago)}),
        "payments": frappe.db.count("Payment", {"creation": (">", week_ago)}),
        "open_complaints": frappe.db.count("Complaint", {"status": "Open"}),
    }

    html = "<ul>" + "".join(f"<li>{k}: {v}</li>" for k, v in stats.items()) + "</ul>"
    frappe.sendmail(
        recipients=managers,
        subject=_("Tuition Center Weekly Digest"),
        message=f"<h3>Weekly Summary</h3>{html}",
    )


def queue_emails():
    """Placeholder to flush queued emails faster if desired."""
    pass


# ------------------------------------------------------------------
# Utils
# ------------------------------------------------------------------


@frappe.whitelist()
def make_payment_for_enrolment(fee_enrolment, amount, mode_of_payment, reference_no=None):
    """Quick 'record payment' from the Fee Enrolment form."""
    if not frappe.has_permission("Payment", "create"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    doc = frappe.get_doc("Fee Enrolment", fee_enrolment)
    doc.add_payment(amount, mode_of_payment, reference_no)
    frappe.db.commit()
    return doc.name


@frappe.whitelist()
def get_announcements():
    """Active announcements for portal users."""
    now = now_datetime()
    return frappe.get_all(
        "Announcement",
        filters={
            "publish_date": ("<=", today()),
        },
        fields=["title", "message", "publish_date", "expiry_date", "type", "pinned"],
        order_by="pinned desc, publish_date desc",
        limit_page_length=10,
    )

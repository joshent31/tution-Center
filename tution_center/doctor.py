# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

"""Site-side diagnostics & repair for the Tuition Center app.

Run from the bench:

    bench --site yoursite.local execute tution_center.doctor.run

It inspects the site, repairs what is missing (Module Def, roles,
doctypes), clears caches, and prints a plain-language report.
"""

import traceback

import frappe

ALL_DOCTYPES = [
    "Academic Term", "Announcement", "Assessment Criterion", "Assessment Structure",
    "Assignment", "Assignment Submission", "Attendance Tool", "Attendance Tool Student",
    "Batch", "Batch Student", "Book", "Book Issue", "Certificate", "Complaint",
    "Course", "Course Assessment", "Exam", "Exam Result", "Exam Result Student",
    "Fee Component", "Fee Enrolment", "Fee Payment Reference", "Fee Schedule",
    "Fee Schedule Student", "Fee Structure", "Guardian", "Guardian Student",
    "Notification Reminder", "Payment", "Room", "Student", "Student Attendance",
    "Student Guardian", "Teacher", "Timetable", "Timetable Slot", "Tuition Settings",
]


def run():
    report = []

    def log(label, value):
        report.append(f"{label:<38} {value}")
        print(f"{label:<38} {value}")

    # 1. is the app installed?
    installed = "tution_center" in frappe.get_installed_apps()
    log("app installed:", installed)
    if not installed:
        print("=> Run: bench --site <site> install-app tution_center")
        return report

    # 2. Module Def present? (breaks all desk routes when missing)
    has_module_def = frappe.db.exists("Module Def", "Tuition Center")
    log("Module Def 'Tuition Center':", has_module_def or "MISSING")
    if not has_module_def:
        frappe.get_doc(
            {"doctype": "Module Def", "module_name": "Tuition Center", "app_name": "tution_center"}
        ).insert(ignore_permissions=True)
        frappe.db.commit()
        print("   -> created Module Def")

    # 3. roles
    from tution_center.install import make_roles

    make_roles()
    frappe.db.commit()
    log("roles ensured:", "Tuition Manager/Teacher, Student, Guardian")

    # 4. which doctypes are actually in the DB?
    present = set(
        frappe.get_all("DocType", filters={"module": "Tuition Center"}, pluck="name")
    )
    missing = [d for d in ALL_DOCTYPES if d not in present]
    log("doctypes in DB:", f"{len(present)}/{len(ALL_DOCTYPES)}")

    if missing:
        print("   missing: " + ", ".join(missing))
        print("   -> forcing full sync of the app ...")
        try:
            from frappe.model.sync import sync_for

            sync_for("tution_center", force=True, reset_permissions=True)
            frappe.db.commit()
            present = set(
                frappe.get_all("DocType", filters={"module": "Tuition Center"}, pluck="name")
            )
            still_missing = [d for d in ALL_DOCTYPES if d not in present]
            log("after sync — doctypes in DB:", f"{len(present)}/{len(ALL_DOCTYPES)}")
            if still_missing:
                log("STILL MISSING after sync:", ", ".join(still_missing))
                print(
                    "   => the sync is failing; scroll up for a traceback and share it"
                )
        except Exception:
            print("=" * 60)
            print("SYNC FAILED with traceback:")
            print(traceback.format_exc())
            print("=" * 60)
            log("sync status:", "FAILED — see traceback above")

    # 5. sample permission sanity (Batch readable by System Manager?)
    if "Batch" in present:
        perms = frappe.get_all(
            "DocPerm", filters={"parent": "Batch"}, fields=["role", "read"]
        )
        log("Batch permission rows:", str([f"{p.role}:{p.read}" for p in perms]))

    # 6. clear caches (desk routes live in Redis)
    frappe.clear_cache()
    log("cache cleared:", "frappe.clear_cache() done")

    print("\nDone. Now reload the desk (Ctrl+Shift+R) and try /app/batch again.")
    return report

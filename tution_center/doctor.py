# Copyright (c) 2026, Joshent and contributors
# For license information, please see license.txt

"""Site-side diagnostics & repair for the Tuition Center app.

Run from the bench:

    bench --site yoursite.local execute tution_center.doctor.run

It inspects the site, repairs what is missing (Module Def, roles,
doctypes), clears caches, and prints a plain-language report.

If any doctype is missing it force-imports every doctype file
INDIVIDUALLY, so the first file that fails names itself exactly —
one broken JSON can no longer silently abort the rest of the sync.
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

CHILD_DOCTYPES = [
    "Attendance Tool Student", "Batch Student", "Course Assessment",
    "Exam Result Student", "Fee Component", "Fee Payment Reference",
    "Fee Schedule Student", "Guardian Student", "Student Guardian", "Timetable Slot",
]


def run():
    report = []

    def log(label, value):
        report.append(f"{label:<38} {value}")
        print(f"{label:<38} {value}")

    # 0. can the module package be imported at all?
    try:
        frappe.get_module("tution_center.tuition_center")
        log("module package import:", "OK")
    except Exception:
        print("=" * 60)
        print("MODULE IMPORT FAILED:")
        print(traceback.format_exc())
        print("=" * 60)
        log("module package import:", "FAILED — see traceback above")
        return report

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
    missing_children = [d for d in CHILD_DOCTYPES if d not in present]
    if missing_children:
        print("   missing CHILD tables: " + ", ".join(missing_children))

    if missing:
        print("   missing: " + ", ".join(missing))

        # 4a. try the normal bulk sync first
        print("   -> forcing full sync of the app ...")
        try:
            from frappe.model.sync import sync_for

            sync_for("tution_center", force=True, reset_permissions=True)
            frappe.db.commit()
        except Exception:
            print("=" * 60)
            print("BULK SYNC FAILED with traceback:")
            print(traceback.format_exc())
            print("=" * 60)
            log("bulk sync status:", "FAILED — see traceback above")

        # 4b. now import every still-missing doctype ONE BY ONE from its
        #     exact file path, so the first bad file names itself.
        present = set(
            frappe.get_all("DocType", filters={"module": "Tuition Center"}, pluck="name")
        )
        still_missing = [d for d in ALL_DOCTYPES if d not in present]
        if still_missing:
            print("   -> importing remaining doctypes one by one ...")
            from frappe.modules.import_file import import_file

            for d in still_missing:
                try:
                    import_file("Tuition Center", d, d, force=True)
                    frappe.db.commit()
                    ok = frappe.db.exists("DocType", d)
                    print(f"   {'OK ' if ok else 'FAIL'}  {d}")
                    if not ok:
                        print(f"       => imported without error but row still missing: {d}")
                except Exception:
                    frappe.db.rollback()
                    print(f"   FAIL  {d}")
                    print("       " + "-" * 56)
                    for line in traceback.format_exc().strip().splitlines()[-6:]:
                        print("       " + line)

        present = set(
            frappe.get_all("DocType", filters={"module": "Tuition Center"}, pluck="name")
        )
        log("after repair — doctypes in DB:", f"{len(present)}/{len(ALL_DOCTYPES)}")
        final_missing = [d for d in ALL_DOCTYPES if d not in present]
        if final_missing:
            log("STILL MISSING:", ", ".join(final_missing))
            print("   => scroll up: the FAIL lines + traceback name the exact files")
        else:
            log("repair status:", "ALL DOCTYPES PRESENT")

    # 5. sample permission sanity (Batch readable by System Manager?)
    if frappe.db.exists("DocType", "Batch"):
        perms = frappe.get_all(
            "DocPerm", filters={"parent": "Batch"}, fields=["role", "read"]
        )
        log("Batch permission rows:", str([f"{p.role}:{p.read}" for p in perms]))

    # 6. clear caches (desk routes live in Redis)
    frappe.clear_cache()
    log("cache cleared:", "frappe.clear_cache() done")

    print("\nDone. Now reload the desk (Ctrl+Shift+R) and try /app/batch again.")
    return report

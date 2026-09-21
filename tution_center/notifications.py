import frappe


def get_notification_config():
    return {
        "for_doctype": {
            "Complaint": {"status": "Open"},
            "Fee Enrolment": {"status": "Unpaid"},
        }
    }

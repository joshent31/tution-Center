app_name = "tution_center"
app_title = "Tuition Center"
app_publisher = "Joshent"
app_description = "Advanced Tuition Centre Management System for Frappe v15+"
app_email = "joshent31@gmail.com"
app_license = "MIT"

# ---------------- Required apps ----------------
required_apps = []

# ---------------- Notifications ----------------
notification_config = "tution_center.notifications.get_notification_config"

# ---------------- Scheduled tasks ----------------
scheduler_events = {
    "daily": [
        "tution_center.api.send_fee_reminders",
    ],
    "weekly": [
        "tution_center.api.send_weekly_digest",
    ],
    "all": [
        "tution_center.api.queue_emails",
    ],
}

# ---------------- Fixtures ----------------
fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "Tuition Center"]]},
    {"dt": "Property Setter", "filters": [["module", "=", "Tuition Center"]]},
]

# ---------------- Website / Portal routes ----------------
website_route_rules = [
    {"from_route": "/tuition/<path:app_path>", "to_route": "tuition"},
]

# ---------------- Standard footer/portal ----------------
# portal hooks
# standard_portal_menu_items are defined via Web Portal Menu doctype in v15

# ---------------- Install / uninstall ----------------
after_install = "tution_center.install.after_install"
before_uninstall = "tution_center.install.before_uninstall"

# ---------------- Permissions ----------------
# permission_query_conditions / has_permission per doctype are handled
# inside each doctype's python controller when needed.

# ---------------- Calendars / views ----------------
# calendar_views = [{"doctype": "Exam"}]

# ---------------- Document actions / global search ----------------
global_search_doctypes = {
    "Course": 1,
    "Student": 2,
    "Batch": 3,
    "Teacher": 4,
    "Fee Enrolment": 5,
}

# ---------------- Extend boot info for portal ----------------
extend_bootinfo = "tution_center.api.extend_bootinfo"

import frappe

no_cache = 1


def get_context(context):
	"""Server context for the mobile app page (public; SPA handles auth state)."""
	context.no_cache = 1
	context.title = "Josh Tuition Centre"

	user = frappe.session.user
	context.logged_in = user != "Guest"
	context.csrf_token = frappe.sessions.get_csrf_token() if context.logged_in else ""
	context.fullname = frappe.db.get_value("User", user, "full_name") if context.logged_in else ""

	context.roles = frappe.get_roles(user) if context.logged_in else []
	context.is_student = "Student" in context.roles
	context.is_guardian = "Guardian" in context.roles
	context.is_teacher = "Tuition Teacher" in context.roles
	context.is_manager = "Tuition Manager" in context.roles or "System Manager" in context.roles

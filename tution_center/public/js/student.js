// Desk helper: link/create the portal user for a Student
frappe.ui.form.on("Student", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.user) {
			frm.dashboard.set_headline(__("Portal user linked: {0}", [frm.doc.user]));
			return;
		}
		frm.add_custom_button(__("Create Portal User"), () => {
			frm
				.call("create_portal_user")
				.then(() => frm.reload_doc());
		});
	},
});

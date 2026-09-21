// Copyright (c) 2026, Joshent and contributors
// For license information, please see license.txt

frappe.ui.form.on("Notification Reminder", {
	refresh(frm) {
		frm.add_custom_button(__("Send Now"), () => {
			frappe.confirm(__("Send this reminder now?"), () => {
				frm.call("send_now").then(() => frm.refresh_fields());
			});
		});
	},
});

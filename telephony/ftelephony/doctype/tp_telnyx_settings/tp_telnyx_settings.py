# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
import telnyx


class TPTelnyxSettings(Document):
    friendly_resource_name = (
        "Frappe Telephony"  # System creates Telnyx app & API keys with this name.
    )

    def validate(self):
        old_api_key = frappe.db.get_single_value(
            "TP Telnyx Settings", "api_key"
        )
        if self.api_key != old_api_key:
            self.new_key = True
        else:
            self.new_key = False
        self.validate_telnyx_account()

    def on_update(self):
        # Single doctype records are created in DB at time of installation and those field values are set as null.
        # This condition make sure that we handle null.
        if not self.api_key:
            return

        telnyx.api_key = self.get_password("api_key")
        self.set_application_credentials(self.app_name)
        self.fetch_applications()

    def validate_telnyx_account(self):
        try:
            telnyx.api_key = self.get_password("api_key")
            # Test the connection by listing phone numbers
            telnyx.PhoneNumber.list()
            return True
        except Exception:
            frappe.throw(_("Invalid API Key or connection failed."))

    def set_application_credentials(self, app_name):
        """Generate Telnyx Call Control App credentials if not exist and update them."""
        credentials = self.get_application(app_name) or self.create_application()
        self.application_id = credentials.id
        self.app_name = credentials.friendly_name
        frappe.db.set_single_value(
            "TP Telnyx Settings",
            {"application_id": self.application_id, "app_name": self.app_name},
        )

    def get_telnyx_voice_url(self):
        url_path = "/api/method/telephony.telnyx.api.voice"
        return get_public_url(url_path)

    def get_application(self, friendly_name=None):
        """Get Call Control App from telnyx account if exists."""
        friendly_name = friendly_name or self.friendly_resource_name
        try:
            applications = telnyx.CallControlApplication.list()
            for app in applications:
                if app.friendly_name == friendly_name:
                    return app
            return None
        except Exception as e:
            frappe.log_error(f"Error getting application: {str(e)}")
            return None

    def create_application(self, friendly_name=None):
        """Create Call Control App in telnyx account."""
        friendly_name = friendly_name or self.friendly_resource_name
        try:
            application = telnyx.CallControlApplication.create(
                webhook_event_url=self.get_telnyx_voice_url(),
                webhook_event_failover_url=self.get_telnyx_voice_url(),
                webhook_timeout_secs=30,
                friendly_name=friendly_name,
            )
            return application
        except Exception as e:
            frappe.log_error(f"Error creating application: {str(e)}")
            frappe.throw(_("Telnyx Call Control App creation error."))

    def fetch_applications(self):
        try:
            applications = telnyx.CallControlApplication.list()
            app_names = [app.friendly_name for app in applications]
            frappe.db.set_single_value(
                "TP Telnyx Settings",
                "telnyx_apps",
                ",".join(app_names),
            )
        except Exception as e:
            frappe.log_error(f"Error fetching applications: {str(e)}")


def get_public_url(path: str | None = None):
    from frappe.utils import get_url

    return get_url().split(":8", 1)[0] + path

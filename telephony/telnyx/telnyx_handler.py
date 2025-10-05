import frappe
from frappe import _
from frappe.utils.password import get_decrypted_password
import telnyx
from telnyx import Call, CallControlApplication
import json

from .utils import get_public_url, merge_dicts


class Telnyx:
    """Telnyx connector over Telnyx SDK."""

    def __init__(self, settings):
        """
        :param settings: `TP Telnyx Settings` doctype
        """
        self.settings = settings
        self.api_key = settings.api_key
        self.connection_id = settings.connection_id
        self.application_id = settings.application_id
        self.telnyx_client = self.get_telnyx_client()

    @classmethod
    def connect(self):
        """Make a telnyx connection."""
        settings = frappe.get_doc("TP Telnyx Settings")
        if not (settings and settings.enabled):
            return
        return Telnyx(settings=settings)

    def get_phone_numbers(self):
        """Get account's telnyx phone numbers."""
        try:
            numbers = telnyx.PhoneNumber.list()
            return [n.phone_number for n in numbers]
        except Exception as e:
            frappe.log_error(f"Error fetching phone numbers: {str(e)}")
            return []

    def generate_voice_access_token(self, identity: str, ttl=60 * 60):
        """Generates a token required to make voice calls from the browser."""
        # For Telnyx, we'll use a different approach since they don't have the same token system as Twilio
        # We'll return a simple token structure that can be used for authentication
        identity = self.safe_identity(identity)
        
        # Create a simple token structure for Telnyx
        token_data = {
            "identity": identity,
            "api_key": self.api_key,
            "connection_id": self.connection_id,
            "application_id": self.application_id,
            "ttl": ttl
        }
        
        # In a real implementation, you might want to use JWT or another secure token method
        import base64
        token = base64.b64encode(json.dumps(token_data).encode()).decode()
        return token

    @classmethod
    def safe_identity(cls, identity: str):
        """Create a safe identity by replacing unsupported special characters `@` with (at)).
        Similar to Twilio's approach for consistency.
        """
        return identity.replace("@", "(at)")

    @classmethod
    def emailid_from_identity(cls, identity: str):
        """Convert safe identity string into emailID."""
        return identity.replace("(at)", "@")

    def get_recording_status_callback_url(self):
        url_path = "/api/method/telephony.telnyx.api.update_recording_info"
        return get_public_url(url_path)

    def get_update_call_status_callback_url(self):
        url_path = "/api/method/telephony.telnyx.api.update_call_status_info"
        return get_public_url(url_path)

    def generate_telnyx_dial_response(self, from_number: str, to_number: str):
        """Generates voice call instructions to forward the call to agents Phone."""
        # Telnyx uses different call control commands
        # This would typically be handled through their Call Control API
        response = {
            "commands": [
                {
                    "command": "answer",
                    "call_control_id": "call_control_id_placeholder"
                },
                {
                    "command": "dial",
                    "to": to_number,
                    "from": from_number,
                    "record": self.settings.record_calls,
                    "recording_status_callback": self.get_recording_status_callback_url(),
                    "status_callback": self.get_update_call_status_callback_url()
                }
            ]
        }
        return response

    def get_call_info(self, call_control_id):
        """Get call information from Telnyx."""
        try:
            call = Call.retrieve(call_control_id)
            return call
        except Exception as e:
            frappe.log_error(f"Error fetching call info: {str(e)}")
            return None

    def generate_telnyx_client_response(self, client, ring_tone="at"):
        """Generates voice call instructions to forward the call to agents computer."""
        # For Telnyx, client calls would be handled differently
        # This is a placeholder implementation
        response = {
            "commands": [
                {
                    "command": "answer",
                    "call_control_id": "call_control_id_placeholder"
                },
                {
                    "command": "dial",
                    "to": client,
                    "ring_tone": ring_tone,
                    "record": self.settings.record_calls,
                    "recording_status_callback": self.get_recording_status_callback_url(),
                    "status_callback": self.get_update_call_status_callback_url()
                }
            ]
        }
        return response

    @classmethod
    def get_telnyx_client(self):
        telnyx_settings = frappe.get_doc("TP Telnyx Settings")
        if not telnyx_settings.enabled:
            frappe.throw(_("Please enable Telnyx to proceed."))

        api_key = get_decrypted_password(
            "TP Telnyx Settings", "TP Telnyx Settings", "api_key"
        )
        
        # Set the API key for Telnyx
        telnyx.api_key = api_key
        return telnyx


class IncomingCall:
    def __init__(self, from_number, to_number, meta=None):
        self.from_number = from_number
        self.to_number = to_number
        self.meta = meta

    def process(self):
        """Process the incoming call
        * Figure out who is going to pick the call (call attender)
        * Check call attender settings and forward the call to Phone
        """
        telnyx = Telnyx.connect()
        owners = get_telnyx_number_owners(self.to_number)
        attender = get_the_call_attender(owners)

        if not attender:
            # Return a response indicating no agent is available
            response = {
                "commands": [
                    {
                        "command": "answer",
                        "call_control_id": "call_control_id_placeholder"
                    },
                    {
                        "command": "say",
                        "payload": _("Agent is unavailable to take the call, please call after some time."),
                        "voice": "female"
                    }
                ]
            }
            return response

        if attender["call_receiving_device"] == "Phone":
            return telnyx.generate_telnyx_dial_response(
                self.from_number, attender["mobile_no"]
            )
        else:
            return telnyx.generate_telnyx_client_response(
                telnyx.safe_identity(attender["name"])
            )


def get_telnyx_number_owners(phone_number):
    """Get list of users who is using the phone_number.
    >>> get_telnyx_number_owners("+11234567890")
    {
            'owner1': {'name': '..', 'mobile_no': '..', 'call_receiving_device': '...'},
            'owner2': {....}
    }
    """
    # remove special characters from phone number and get only digits also remove white spaces
    # keep + sign in the number at start of the number
    phone_number = "".join([c for c in phone_number if c.isdigit() or c == "+"])
    user_voice_settings = frappe.get_all(
        "TP Telephony Agent",
        filters={"telnyx_number": phone_number},
        fields=["name", "call_receiving_device"],
    )
    user_wise_voice_settings = {user["name"]: user for user in user_voice_settings}

    user_general_settings = frappe.get_all(
        "User",
        filters=[["name", "IN", user_wise_voice_settings.keys()]],
        fields=["name", "mobile_no"],
    )
    user_wise_general_settings = {user["name"]: user for user in user_general_settings}

    return merge_dicts(user_wise_general_settings, user_wise_voice_settings)


def get_active_loggedin_users(users):
    """Filter the current loggedin users from the given users list"""
    rows = frappe.db.sql(
        """
		SELECT `user`
		FROM `tabSessions`
		WHERE `user` IN %(users)s
		""",
        {"users": users},
    )
    return [row[0] for row in set(rows)]


def get_the_call_attender(owners):
    """Get attender details from list of owners"""
    if not owners:
        return
    current_loggedin_users = get_active_loggedin_users(list(owners.keys()))

    for name, details in owners.items():
        if (details["call_receiving_device"] == "Phone" and details["mobile_no"]) or (
            details["call_receiving_device"] == "Computer"
            and name in current_loggedin_users
        ):
            return details


class TelnyxCallDetails:
    def __init__(self, call_info, call_from=None, call_to=None):
        self.call_info = call_info
        self.connection_id = call_info.get("connection_id")
        self.application_id = call_info.get("application_id")
        self.call_control_id = call_info.get("call_control_id")
        self.call_status = self.get_call_status(call_info.get("call_state"))
        self._call_from = call_from or call_info.get("from")
        self._call_to = call_to or call_info.get("to")

    def get_direction(self):
        # Telnyx uses different field names for direction
        if self.call_info.get("direction") == "outbound":
            return "Outgoing"
        return "Incoming"

    def get_from_number(self):
        return self._call_from or self.call_info.get("from")

    def get_to_number(self):
        return self._call_to or self.call_info.get("to")

    @classmethod
    def get_call_status(cls, telnyx_status):
        """Convert Telnyx given status into system status."""
        telnyx_status = telnyx_status or ""
        # Map Telnyx call states to system status
        status_mapping = {
            "parked": "Parked",
            "bridging": "Bridging", 
            "bridged": "Bridged",
            "hangup": "Hangup",
            "answered": "Answered",
            "ringing": "Ringing"
        }
        return status_mapping.get(telnyx_status.lower(), telnyx_status.title())

    def to_dict(self):
        """Convert call details into dict."""
        direction = self.get_direction()
        from_number = self.get_from_number()
        to_number = self.get_to_number()
        caller = ""
        receiver = ""

        if direction == "Outgoing":
            caller = self.call_info.get("caller_id_name", "")
            # For outgoing calls, caller is the user making the call
            if caller:
                identity = caller.replace("client:", "").strip()
                caller = Telnyx.emailid_from_identity(identity) if identity else ""
        else:
            owners = get_telnyx_number_owners(to_number)
            attender = get_the_call_attender(owners)
            receiver = attender["name"] if attender else ""

        return {
            "type": direction,
            "status": self.call_status,
            "id": self.call_control_id,
            "from": from_number,
            "to": to_number,
            "receiver": receiver,
            "caller": caller,
        }

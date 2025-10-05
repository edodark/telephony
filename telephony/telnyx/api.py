import json

import frappe
from frappe import _
from werkzeug.wrappers import Response

from telephony.utils import link_call_with_contact, link_call_with_doc

from .telnyx_handler import IncomingCall, Telnyx, TelnyxCallDetails


@frappe.whitelist()
def is_enabled():
    return frappe.db.get_single_value("TP Telnyx Settings", "enabled")


@frappe.whitelist()
def generate_access_token():
    """Returns access token that is required to authenticate Telnyx Client SDK."""
    telnyx = Telnyx.connect()
    if not telnyx:
        return {}

    from_number = frappe.db.get_value(
        "TP Telephony Agent",
        {"user": frappe.session.user},
        "telnyx_number",
    )
    if not from_number:
        return {
            "ok": False,
            "error": "caller_phone_identity_missing",
            "detail": "Phone number is not mapped to the caller",
        }

    token = telnyx.generate_voice_access_token(identity=frappe.session.user)
    return {"token": token}


@frappe.whitelist(allow_guest=True)
def voice(**kwargs):
    """This is a webhook called by telnyx to get instructions when the voice call request comes to telnyx server."""

    def _get_caller_number(caller):
        identity = caller.replace("client:", "").strip()
        user = Telnyx.emailid_from_identity(identity)
        return frappe.db.get_value("TP Telephony Agent", user, "telnyx_number")

    args = frappe._dict(kwargs)
    telnyx = Telnyx.connect()
    if not telnyx:
        return

    # Validate the webhook (you might want to add signature validation)
    # assert args.connection_id == telnyx.connection_id
    # assert args.application_id == telnyx.application_id

    # Generate Telnyx call control instructions to make a call
    from_number = _get_caller_number(args.get("caller_id_name", ""))
    resp = telnyx.generate_telnyx_dial_response(from_number, args.get("to"))

    call_details = TelnyxCallDetails(args, call_from=from_number)
    create_call_log(
        call_details,
        link_doc={"doctype": args.get("link_doctype"), "docname": args.get("link_docname")},
    )
    return Response(json.dumps(resp), mimetype="application/json")


@frappe.whitelist(allow_guest=True)
def telnyx_incoming_call_handler(**kwargs):
    args = frappe._dict(kwargs)
    call_details = TelnyxCallDetails(args)
    create_call_log(call_details)

    resp = IncomingCall(args.get("from"), args.get("to")).process()
    return Response(json.dumps(resp), mimetype="application/json")


def create_call_log(call_details: TelnyxCallDetails, link_doc=None):
    details = call_details.to_dict()

    call_log = frappe.get_doc(
        {**details, "doctype": "TP Call Log", "telephony_medium": "Telnyx"}
    )

    contact_number = (
        details.get("from") if details.get("type") == "Incoming" else details.get("to")
    )
    link_call_with_contact(contact_number, call_log)

    if link_doc and link_doc["doctype"] and link_doc["docname"]:
        link_call_with_doc(call_log, link_doc["doctype"], link_doc["docname"])

    call_log.save(ignore_permissions=True)
    frappe.db.commit()  # nosemgrep
    return call_log


def update_call_log(call_control_id, status=None):
    """Update call log status."""
    telnyx = Telnyx.connect()
    if not (telnyx and frappe.db.exists("TP Call Log", call_control_id)):
        return

    # Retry logic for update conflict when multiple requests are made
    MAX_RETRIES = 3
    for i in range(MAX_RETRIES):
        try:
            call_details = telnyx.get_call_info(call_control_id)
            call_log = frappe.get_doc("TP Call Log", call_control_id)

            call_log.status = TelnyxCallDetails.get_call_status(
                status or call_details.call_state if call_details else status
            )
            if call_details:
                call_log.duration = getattr(call_details, 'duration', 0)
                call_log.start_time = get_datetime_from_timestamp(getattr(call_details, 'started_at', None))
                call_log.end_time = get_datetime_from_timestamp(getattr(call_details, 'ended_at', None))

            call_log.save(ignore_permissions=True)
            frappe.db.commit()  # nosemgrep
            return call_log

        except frappe.exceptions.TimestampMismatchError:
            frappe.clear_messages()
            if i == MAX_RETRIES - 1:
                frappe.log_error(
                    f"Failed to update call log {call_control_id} after {MAX_RETRIES} retries",
                    "Call Log Update Error",
                )
                raise
            # Auto-retry will fetch fresh document on next iteration
            continue

        except Exception as e:
            frappe.log_error(
                f"Error while updating call record: {str(e)}\n{frappe.get_traceback()}",
                "Call Log Update Error",
            )
            frappe.db.commit()  # nosemgrep
            break
    return


@frappe.whitelist(allow_guest=True)
def update_recording_info(**kwargs):
    try:
        args = frappe._dict(kwargs)
        recording_url = args.get("recording_url")
        call_control_id = args.get("call_control_id")
        update_call_log(call_control_id)
        frappe.db.set_value("TP Call Log", call_control_id, "recording_url", recording_url)
    except Exception:
        frappe.log_error(title=_("Failed to capture Telnyx recording"))


@frappe.whitelist(allow_guest=True)
def update_call_status_info(**kwargs):
    try:
        args = frappe._dict(kwargs)
        parent_call_control_id = args.get("parent_call_control_id")
        update_call_log(parent_call_control_id, status=args.get("call_state"))

        call_info = {
            "parent_call_control_id": args.get("parent_call_control_id"),
            "call_control_id": args.get("call_control_id"),
            "call_state": args.get("call_state"),
            "call_duration": args.get("call_duration"),
            "from": args.get("from"),
            "to": args.get("to"),
        }

        # For Telnyx, we might not need to send user defined messages like Twilio
        # This is a placeholder for any additional call status handling
        frappe.log_error(f"Call status update: {json.dumps(call_info)}", "Telnyx Call Status Update")
    except Exception:
        frappe.log_error(title=_("Failed to update Telnyx call status"))


def get_datetime_from_timestamp(timestamp):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    if not timestamp:
        return None

    # Handle different timestamp formats that Telnyx might use
    if isinstance(timestamp, str):
        try:
            # Try parsing ISO format
            datetime_utc_tz = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            # Fallback to other formats if needed
            return None
    else:
        datetime_utc_tz = timestamp

    system_timezone = frappe.utils.get_system_timezone()
    converted_datetime = datetime_utc_tz.astimezone(ZoneInfo(system_timezone))
    return frappe.utils.format_datetime(converted_datetime, "yyyy-MM-dd HH:mm:ss")


@frappe.whitelist()
def fetch_applications():
    telnyx = Telnyx.get_telnyx_client()
    try:
        applications = telnyx.CallControlApplication.list()
        app_names = [app.friendly_name for app in applications]
        frappe.db.set_single_value(
            "TP Telnyx Settings",
            "telnyx_apps",
            ",".join(app_names),
        )
        return app_names
    except Exception as e:
        frappe.log_error(f"Error fetching applications: {str(e)}")
        return []

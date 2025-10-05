# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import unittest
import frappe
from telephony.telnyx.telnyx_handler import Telnyx, TelnyxCallDetails


class TestTelnyxIntegration(unittest.TestCase):
    """Test cases for Telnyx integration"""

    def setUp(self):
        """Set up test data"""
        self.test_call_info = {
            "connection_id": "test_connection_123",
            "application_id": "test_app_456", 
            "call_control_id": "test_call_789",
            "call_state": "answered",
            "from": "+1234567890",
            "to": "+0987654321",
            "direction": "inbound"
        }

    def test_telnyx_call_details_creation(self):
        """Test TelnyxCallDetails class creation and methods"""
        call_details = TelnyxCallDetails(self.test_call_info)
        
        # Test basic properties
        self.assertEqual(call_details.connection_id, "test_connection_123")
        self.assertEqual(call_details.application_id, "test_app_456")
        self.assertEqual(call_details.call_control_id, "test_call_789")
        
        # Test direction detection
        self.assertEqual(call_details.get_direction(), "Incoming")
        
        # Test number extraction
        self.assertEqual(call_details.get_from_number(), "+1234567890")
        self.assertEqual(call_details.get_to_number(), "+0987654321")
        
        # Test status conversion
        self.assertEqual(call_details.get_call_status("answered"), "Answered")
        self.assertEqual(call_details.get_call_status("ringing"), "Ringing")
        self.assertEqual(call_details.get_call_status("hangup"), "Hangup")

    def test_telnyx_call_details_to_dict(self):
        """Test conversion of call details to dictionary"""
        call_details = TelnyxCallDetails(self.test_call_info)
        result = call_details.to_dict()
        
        # Verify required fields are present
        self.assertIn("type", result)
        self.assertIn("status", result)
        self.assertIn("id", result)
        self.assertIn("from", result)
        self.assertIn("to", result)
        self.assertIn("receiver", result)
        self.assertIn("caller", result)
        
        # Verify values
        self.assertEqual(result["type"], "Incoming")
        self.assertEqual(result["status"], "Answered")
        self.assertEqual(result["id"], "test_call_789")
        self.assertEqual(result["from"], "+1234567890")
        self.assertEqual(result["to"], "+0987654321")

    def test_telnyx_safe_identity(self):
        """Test identity safety functions"""
        # Test safe identity conversion
        safe_identity = Telnyx.safe_identity("user@example.com")
        self.assertEqual(safe_identity, "user(at)example.com")
        
        # Test email conversion back
        email = Telnyx.emailid_from_identity("user(at)example.com")
        self.assertEqual(email, "user@example.com")

    def test_outgoing_call_details(self):
        """Test outgoing call details handling"""
        outgoing_call_info = {
            "connection_id": "test_connection_123",
            "application_id": "test_app_456",
            "call_control_id": "test_call_789", 
            "call_state": "answered",
            "from": "+1234567890",
            "to": "+0987654321",
            "direction": "outbound",
            "caller_id_name": "client:user(at)example.com"
        }
        
        call_details = TelnyxCallDetails(outgoing_call_info)
        result = call_details.to_dict()
        
        self.assertEqual(result["type"], "Outgoing")
        self.assertEqual(result["caller"], "user@example.com")

    def test_call_status_mapping(self):
        """Test call status mapping from Telnyx to system status"""
        status_tests = [
            ("parked", "Parked"),
            ("bridging", "Bridging"),
            ("bridged", "Bridged"), 
            ("hangup", "Hangup"),
            ("answered", "Answered"),
            ("ringing", "Ringing"),
            ("unknown_status", "Unknown_status")
        ]
        
        for telnyx_status, expected_status in status_tests:
            result = TelnyxCallDetails.get_call_status(telnyx_status)
            self.assertEqual(result, expected_status)


if __name__ == "__main__":
    unittest.main()

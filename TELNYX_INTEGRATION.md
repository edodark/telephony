# Telnyx Integration for ERPNext Telephony

This document describes the Telnyx integration that has been added to the ERPNext telephony app, providing feature parity with the existing Twilio integration.

## Overview

The Telnyx integration provides the same functionality as Twilio, including:
- Outgoing voice calls from the browser
- Incoming call handling and routing
- Call recording capabilities
- Call status tracking and logging
- Webhook handling for real-time updates

## Architecture

The integration follows the same architectural pattern as the Twilio implementation:

```
telephony/
├── telnyx/
│   ├── __init__.py
│   ├── api.py                    # API endpoints and webhook handlers
│   ├── telnyx_handler.py         # Core Telnyx integration logic
│   ├── utils.py                  # Utility functions
│   └── test_telnyx_integration.py # Test cases
└── ftelephony/
    └── doctype/
        └── tp_telnyx_settings/   # Telnyx configuration doctype
            ├── __init__.py
            ├── tp_telnyx_settings.py
            ├── tp_telnyx_settings.json
            ├── tp_telnyx_settings.js
            └── test_tp_telnyx_settings.py
```

## Key Components

### 1. Telnyx Settings (TP Telnyx Settings)

A single doctype that stores Telnyx configuration:
- **API Key**: Telnyx API authentication key
- **Connection ID**: Telnyx connection identifier
- **Application ID**: Call Control Application ID (auto-generated)
- **App Name**: Friendly name for the application
- **Record Calls**: Enable/disable call recording
- **Enabled**: Master switch for Telnyx integration

### 2. Telnyx Handler (`telnyx_handler.py`)

Core integration logic including:
- **Telnyx Class**: Main connector class for Telnyx API
- **IncomingCall Class**: Handles incoming call processing
- **TelnyxCallDetails Class**: Processes call information
- **Utility Functions**: Helper functions for call routing

### 3. API Endpoints (`api.py`)

Webhook and API endpoints:
- `voice()`: Handles outgoing call webhooks
- `telnyx_incoming_call_handler()`: Handles incoming call webhooks
- `generate_access_token()`: Generates authentication tokens
- `update_call_log()`: Updates call status and details
- `update_recording_info()`: Handles recording webhooks
- `update_call_status_info()`: Handles call status webhooks

### 4. Telephony Agent Updates

The `TP Telephony Agent` doctype has been updated to include:
- **Telnyx checkbox**: Enable Telnyx for the agent
- **Telnyx Number**: Phone number associated with the agent
- **Default Medium**: Now includes "Telnyx" as an option

## Configuration

### 1. Install Dependencies

The Telnyx Python SDK has been added to `pyproject.toml`:
```toml
dependencies = [
    "twilio==8.5.0",
    "telnyx==2.0.0"
]
```

### 2. Configure Telnyx Settings

1. Go to **TP Telnyx Settings** in ERPNext
2. Enable the integration
3. Enter your Telnyx API Key
4. Enter your Connection ID
5. The system will automatically create a Call Control Application
6. Configure call recording preferences

### 3. Configure Telephony Agents

1. Go to **TP Telephony Agent** for each user
2. Check the "Telnyx" checkbox
3. Enter the Telnyx phone number for the agent
4. Set the default calling medium to "Telnyx" if desired

## API Differences from Twilio

### Call Control

Telnyx uses a different call control model:
- **Twilio**: Uses TwiML for call instructions
- **Telnyx**: Uses JSON commands for call control

### Webhook Format

Telnyx webhooks use different field names:
- `CallSid` → `call_control_id`
- `CallStatus` → `call_state`
- `AccountSid` → `connection_id`
- `ApplicationSid` → `application_id`

### Status Mapping

Telnyx call states are mapped to system statuses:
- `parked` → `Parked`
- `bridging` → `Bridging`
- `bridged` → `Bridged`
- `hangup` → `Hangup`
- `answered` → `Answered`
- `ringing` → `Ringing`

## Webhook Configuration

### Outgoing Calls
- **URL**: `/api/method/telephony.telnyx.api.voice`
- **Method**: POST
- **Content-Type**: application/json

### Incoming Calls
- **URL**: `/api/method/telephony.telnyx.api.telnyx_incoming_call_handler`
- **Method**: POST
- **Content-Type**: application/json

### Call Status Updates
- **URL**: `/api/method/telephony.telnyx.api.update_call_status_info`
- **Method**: POST
- **Content-Type**: application/json

### Recording Updates
- **URL**: `/api/method/telephony.telnyx.api.update_recording_info`
- **Method**: POST
- **Content-Type**: application/json

## Testing

Run the test suite to verify the integration:

```bash
# Run Telnyx-specific tests
python -m pytest telephony/telnyx/test_telnyx_integration.py

# Run all telephony tests
python -m pytest telephony/
```

## Usage

### Making Outgoing Calls

1. Click the phone icon next to a contact's number
2. The system will use the user's default calling medium
3. If Telnyx is the default, it will initiate a call through Telnyx

### Receiving Incoming Calls

1. Incoming calls are automatically routed based on the called number
2. The system finds the appropriate agent based on their Telnyx number
3. Calls are forwarded to the agent's configured device (phone or computer)

### Call Logging

All calls are automatically logged in the **TP Call Log** doctype with:
- Call direction (Incoming/Outgoing)
- Call status and duration
- Recording URL (if enabled)
- Linked contacts and documents

## Troubleshooting

### Common Issues

1. **API Key Invalid**: Verify the API key in Telnyx Mission Control
2. **Connection ID Invalid**: Ensure the Connection ID is correct
3. **Webhook Not Receiving**: Check webhook URLs in Telnyx settings
4. **Calls Not Routing**: Verify agent Telnyx number configuration

### Debugging

Enable debug logging in ERPNext to see detailed Telnyx API interactions:
```python
import frappe
frappe.log_error("Debug message", "Telnyx Debug")
```

## Security Considerations

1. **API Keys**: Store securely using Frappe's password field type
2. **Webhook Validation**: Implement signature validation for production
3. **Access Control**: Use appropriate permissions for Telnyx settings
4. **HTTPS**: Ensure all webhook URLs use HTTPS in production

## Future Enhancements

Potential improvements for the Telnyx integration:
1. **SMS Support**: Add SMS messaging capabilities
2. **Advanced Call Control**: Implement more sophisticated call routing
3. **Analytics**: Add call analytics and reporting
4. **Multi-tenant**: Support for multiple Telnyx accounts
5. **Real-time Updates**: WebSocket support for real-time call status

## Support

For issues with the Telnyx integration:
1. Check the ERPNext error logs
2. Verify Telnyx account configuration
3. Test webhook endpoints manually
4. Review the test cases for expected behavior

## Migration from Twilio

To migrate from Twilio to Telnyx:
1. Configure Telnyx settings
2. Update agent configurations to use Telnyx numbers
3. Update default calling medium to "Telnyx"
4. Test the integration thoroughly
5. Update webhook URLs in external systems
6. Monitor call logs for any issues

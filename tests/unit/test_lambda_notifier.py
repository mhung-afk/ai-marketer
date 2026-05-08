import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

# Add src and lambda directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/lambdas/notifier")))

import lambda_function

@pytest.fixture
def sns_event():
    with open(os.path.abspath(os.path.join(os.path.dirname(__file__), "../fixtures/sample_data.json")), "r") as f:
        data = json.load(f)
        sns_body = data["sns_messages"][0]["body"]
        
    return {
        "Records": [
            {
                "Sns": {
                    "Message": json.dumps(sns_body)
                }
            }
        ]
    }

@patch("lambda_function.get_parameter")
@patch("urllib.request.urlopen")
def test_lambda_handler_success(mock_urlopen, mock_get_parameter, sns_event):
    # Mock parameters
    mock_get_parameter.side_effect = lambda name, **kwargs: {
        "/healing-bedroom/telegram-bot-token": "fake-token",
        "/healing-bedroom/telegram-chat-id": "fake-chat-id"
    }.get(name)

    # Mock Telegram response
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"ok": True}).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    # Invoke handler
    response = lambda_function.lambda_handler(sns_event, None)

    # Assertions
    assert response["statusCode"] == 200
    assert "Budget alert notification sent to Telegram" in response["body"]
    mock_get_parameter.assert_any_call("/healing-bedroom/telegram-bot-token", with_decryption=True)
    mock_get_parameter.assert_any_call("/healing-bedroom/telegram-chat-id")
    assert mock_urlopen.called

@patch("lambda_function.get_parameter")
def test_lambda_handler_missing_params(mock_get_parameter, sns_event):
    # Mock parameters returning None
    mock_get_parameter.return_value = None

    # Invoke handler
    response = lambda_function.lambda_handler(sns_event, None)

    # Assertions
    assert response["statusCode"] == 500
    assert "Telegram credentials not configured" in response["body"]

@patch("lambda_function.get_parameter")
@patch("urllib.request.urlopen")
def test_lambda_handler_telegram_error(mock_urlopen, mock_get_parameter, sns_event):
    # Mock parameters
    mock_get_parameter.side_effect = ["fake-token", "fake-chat-id"]

    # Mock Telegram error
    mock_urlopen.side_effect = Exception("Connection error")

    # Invoke handler
    response = lambda_function.lambda_handler(sns_event, None)

    # Assertions
    assert response["statusCode"] == 500
    assert "Failed to send Telegram message" in response["body"]

def test_send_telegram_message_cleaning():
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"ok": True}).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response
        
        # Call with messy inputs
        lambda_function.send_telegram_message(" token\n", " chat_id ", " msg ")
        
        # Verify the URL was constructed with cleaned token
        args, _ = mock_urlopen.call_args
        req = args[0]
        assert req.full_url == "https://api.telegram.org/bottoken/sendMessage"
        
        # Verify the payload was constructed with cleaned chat_id and message
        data = json.loads(req.data.decode("utf-8"))
        assert data["chat_id"] == "chat_id"
        assert data["text"] == "msg"

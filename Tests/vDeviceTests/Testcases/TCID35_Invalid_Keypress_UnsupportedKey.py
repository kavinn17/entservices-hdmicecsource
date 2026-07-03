"""
/**
 * @file TCID35_Invalid_Keypress_UnsupportedKey.py
 * @brief Validate unsupported key handling for sendKeyPressEvent.
 */
"""

import json
import os
import time

from utils import send_curl_command, log_success, log_error, log_warning
import HdmiCECSource_Curl as HdmiCecSourceApis


def _is_expected_failure(resp_body):
    if not isinstance(resp_body, dict):
        return False

    if "error" in resp_body:
        return True

    result = resp_body.get("result", {})
    if isinstance(result, dict) and result.get("success") is False:
        return True

    return False


def _is_framework_validation_error(resp_body):
    if not isinstance(resp_body, dict):
        return False
    err = resp_body.get("error")
    if not isinstance(err, dict):
        return False
    return err.get("code") == -32602


def run_test():
    start_time = time.perf_counter()

    response = send_curl_command(HdmiCecSourceApis.send_key_press_event_invalid_key)
    if not response:
        log_error("✖ sendKeyPressEvent(invalid keyCode) command not sent")
        return False

    log_warning(f"Response: {response}")

    try:
        body = json.loads(response)
    except json.JSONDecodeError:
        log_error("TCID35_Invalid_Keypress_UnsupportedKey Failed: invalid JSON response")
        return False

    if _is_framework_validation_error(body):
        log_error("TCID35 failed: request rejected at JSON-RPC validation layer; plugin branch not exercised")
        return False

    if _is_expected_failure(body):
        elapsed = time.perf_counter() - start_time
        msg = "TCID35_Invalid_Keypress_UnsupportedKey Passed ✅"
        if os.environ.get("HDMICEC_TIMING_ENABLED"):
            log_success(f"{msg} time consumed: {elapsed:.3f}s")
        else:
            log_success(msg)
        return True

    log_error("TCID35_Invalid_Keypress_UnsupportedKey Failed ❌")
    return False

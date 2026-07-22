"""
/**
 * @file TCID37_Disabled_CEC_Negative_Actions.py
 * @brief Validate failure behavior of standby/OTP actions while CEC is disabled.
 */
"""

import json
import os
import time

from utils import send_curl_command, log_success, log_error, log_warning
import HdmiCECSource_Curl as HdmiCecSourceApis


def _is_failure_response(resp_text):
    try:
        body = json.loads(resp_text)
    except Exception:
        return False

    if "error" in body:
        return True

    result = body.get("result", {})
    return isinstance(result, dict) and result.get("success") is False


def _is_success_response(resp_text):
    try:
        body = json.loads(resp_text)
    except Exception:
        return False

    if "error" in body:
        return False

    result = body.get("result", {})
    return isinstance(result, dict) and result.get("success") is True


def run_test():
    start_time = time.perf_counter()

    # Force disabled state first.
    disable_resp = send_curl_command(HdmiCecSourceApis.set_enabled_false)
    if not disable_resp:
        log_error("✖ setEnabled(false) command not sent")
        return False

    time.sleep(1)

    standby_resp = send_curl_command(HdmiCecSourceApis.send_standby_message)
    otp_resp = send_curl_command(HdmiCecSourceApis.perform_otp_action)

    if not standby_resp or not otp_resp:
        log_error("✖ negative action commands not sent")
        return False

    log_warning(f"standby response: {standby_resp}")
    log_warning(f"performOTPAction response: {otp_resp}")

    standby_failed = _is_failure_response(standby_resp)
    otp_failed = _is_failure_response(otp_resp)

    # Restore enabled state so subsequent testcases are not impacted.
    enable_resp = send_curl_command(HdmiCecSourceApis.set_enabled_true)
    restored = bool(enable_resp and _is_success_response(enable_resp))

    if standby_failed and otp_failed and restored:
        elapsed = time.perf_counter() - start_time
        msg = "TCID37_Disabled_CEC_Negative_Actions Passed ✅"
        if os.environ.get("HDMICEC_TIMING_ENABLED"):
            log_success(f"{msg} time consumed: {elapsed:.3f}s")
        else:
            log_success(msg)
        return True

    log_error("TCID37_Disabled_CEC_Negative_Actions Failed ❌")
    return False

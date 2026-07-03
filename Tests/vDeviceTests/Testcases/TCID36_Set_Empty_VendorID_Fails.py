"""
/**
 * @file TCID36_Set_Empty_VendorID_Fails.py
 * @brief Validate empty vendorid handling and value stability.
 */
"""

import json
import os
import time

from utils import send_curl_command, log_success, log_error, log_warning
import HdmiCECSource_Curl as HdmiCecSourceApis


def _extract_vendor_id(resp_text):
    try:
        body = json.loads(resp_text)
        return body.get("result", {}).get("vendorid")
    except Exception:
        return None


def _is_failure_response(resp_text):
    try:
        body = json.loads(resp_text)
    except Exception:
        return False

    if "error" in body:
        return True
    result = body.get("result", {})
    return isinstance(result, dict) and result.get("success") is False


def _is_framework_validation_error(resp_text):
    try:
        body = json.loads(resp_text)
    except Exception:
        return False
    err = body.get("error")
    return isinstance(err, dict) and err.get("code") == -32602


def run_test():
    start_time = time.perf_counter()

    baseline = send_curl_command(HdmiCecSourceApis.get_vendor_id)
    if not baseline:
        log_error("✖ baseline getVendorId command not sent")
        return False

    before_vendor = _extract_vendor_id(baseline)
    if not before_vendor:
        log_error("TCID36_Set_Empty_VendorID_Fails Failed: baseline vendorid unavailable")
        return False

    set_empty = send_curl_command(HdmiCecSourceApis.set_vendor_id_empty)
    if not set_empty:
        log_error("✖ setVendorId(empty) command not sent")
        return False
    log_warning(f"setVendorId(empty) response: {set_empty}")

    if _is_framework_validation_error(set_empty):
        log_error("TCID36 failed: setVendorId(empty) rejected at JSON-RPC validation layer")
        return False

    final_get = send_curl_command(HdmiCecSourceApis.get_vendor_id)
    if not final_get:
        log_error("✖ final getVendorId command not sent")
        return False

    after_vendor = _extract_vendor_id(final_get)

    if _is_failure_response(set_empty) and before_vendor == after_vendor:
        elapsed = time.perf_counter() - start_time
        msg = "TCID36_Set_Empty_VendorID_Fails Passed ✅"
        if os.environ.get("HDMICEC_TIMING_ENABLED"):
            log_success(f"{msg} time consumed: {elapsed:.3f}s")
        else:
            log_success(msg)
        return True

    log_error("TCID36_Set_Empty_VendorID_Fails Failed ❌")
    return False

"""
/**
 * @file TCID39_Set_VendorID_OutOfRange_Defaults.py
 * @brief Validate out-of-range vendor-id is handled in plugin and defaults are applied.
 */
"""

import json
import os
import time

from utils import send_curl_command, log_success, log_error, log_warning
import HdmiCECSource_Curl as HdmiCecSourceApis

EXPECTED_DEFAULT_VENDOR = "0019FB"


def _parse_json(text):
    try:
        return json.loads(text)
    except Exception:
        return None


def _is_framework_validation_error(body):
    if not isinstance(body, dict):
        return False
    err = body.get("error")
    return isinstance(err, dict) and err.get("code") == -32602


def _normalize_vendor(v):
    if not isinstance(v, str):
        return ""
    cleaned = v.replace(":", "").replace("x", "").replace("X", "")
    cleaned = cleaned.upper()
    if cleaned.startswith("0") and len(cleaned) == 5:
        cleaned = "0" + cleaned
    return cleaned


def run_test():
    start_time = time.perf_counter()

    set_resp = send_curl_command(HdmiCecSourceApis.set_vendor_id_out_of_range)
    if not set_resp:
        log_error("✖ setVendorId(out-of-range) command not sent")
        return False
    log_warning(f"setVendorId(out-of-range) response: {set_resp}")

    set_body = _parse_json(set_resp)
    if set_body is None:
        log_error("TCID39 failed: invalid JSON response")
        return False

    if _is_framework_validation_error(set_body):
        log_error("TCID39 failed: request rejected before plugin SetVendorId catch block")
        return False

    get_resp = send_curl_command(HdmiCecSourceApis.get_vendor_id)
    if not get_resp:
        log_error("✖ getVendorId command not sent")
        return False
    log_warning(f"getVendorId response: {get_resp}")

    get_body = _parse_json(get_resp)
    if not isinstance(get_body, dict):
        log_error("TCID39 failed: getVendorId invalid JSON")
        return False

    vendor = get_body.get("result", {}).get("vendorid", "")
    if _normalize_vendor(vendor) == EXPECTED_DEFAULT_VENDOR:
        elapsed = time.perf_counter() - start_time
        msg = "TCID39_Set_VendorID_OutOfRange_Defaults Passed ✅"
        if os.environ.get("HDMICEC_TIMING_ENABLED"):
            log_success(f"{msg} time consumed: {elapsed:.3f}s")
        else:
            log_success(msg)
        return True

    log_error("TCID39_Set_VendorID_OutOfRange_Defaults Failed ❌")
    return False

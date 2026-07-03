"""
/**
 * @file TCID44_Explicit_Plugin_Deactivate_Recover.py
 * @brief Coverage-focused HDMI CEC Source testcase.
 *
 * @testcase TCID44_Explicit_Plugin_Deactivate_Recover
 * @details Performs explicit Controller lifecycle sequence (activate,
 *          status, deactivate, status, reactivate) with sanity checks.
 */
"""

import json
import os
import time

from utils import (
    send_jsonrpc_command,
    send_curl_command,
    log_info,
    log_success,
    log_warning,
    log_error,
)
import HdmiCECSource_Curl as HdmiCecSourceApis


CALLSIGN = "org.rdk.HdmiCecSource"


def _controller(method, request_id, params=None):
    if params is None:
        params = {"callsign": CALLSIGN}
    return send_jsonrpc_command(f"Controller.1.{method}", params=params, request_id=request_id)


def _status(request_id):
    # Some images accept status with callsign params, some return generic payloads.
    with_callsign = _controller("status", request_id, params={"callsign": CALLSIGN})
    if isinstance(with_callsign, dict) and "error" not in with_callsign:
        return with_callsign
    return send_jsonrpc_command("Controller.1.status", request_id=request_id)


def _plugin_alive():
    response = send_curl_command(HdmiCecSourceApis.get_enabled)
    if not response or response.startswith("< No response"):
        return False
    try:
        body = json.loads(response)
        return isinstance(body, dict) and "error" not in body and "result" in body
    except json.JSONDecodeError:
        return False


def _ok(resp):
    return isinstance(resp, dict) and "error" not in resp


def run_test():
    start = time.perf_counter()
    log_info("TCID44 - Scenario: explicit plugin deactivate/recover lifecycle")

    # Ensure known start state.
    act1 = _controller("activate", 5101)
    log_warning(f"  activate #1: {act1}")
    if not _ok(act1):
        log_warning("  activate #1 returned non-success (continuing)")

    time.sleep(1)
    st1 = _status(5102)
    log_warning(f"  status #1: {st1}")
    if not _ok(st1):
        log_error("  status before deactivation failed")
        return False

    if not _plugin_alive():
        log_error("  plugin API not healthy before deactivation")
        return False

    deact = _controller("deactivate", 5103)
    log_warning(f"  deactivate: {deact}")
    if not _ok(deact):
        log_warning("  deactivate returned non-success (continuing)")

    time.sleep(2)
    st2 = _status(5104)
    log_warning(f"  status #2 after deactivate: {st2}")
    if not _ok(st2):
        log_warning("  status after deactivation returned non-success (continuing)")

    act2 = _controller("activate", 5105)
    log_warning(f"  activate #2: {act2}")
    if not _ok(act2):
        log_warning("  activate #2 returned non-success (continuing)")

    time.sleep(2)
    st3 = _status(5106)
    log_warning(f"  status #3 after reactivate: {st3}")

    if not _plugin_alive():
        log_error("  plugin API not healthy after reactivation")
        return False

    elapsed = time.perf_counter() - start
    msg = "TCID44_Explicit_Plugin_Deactivate_Recover Passed ✅"
    if os.environ.get("HDMICEC_TIMING_ENABLED"):
        log_success(f"{msg} time consumed: {elapsed:.3f}s")
    else:
        log_success(msg)
    return True

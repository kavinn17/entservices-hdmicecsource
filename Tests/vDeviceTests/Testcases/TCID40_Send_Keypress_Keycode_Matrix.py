"""
/**
 * @file TCID40_Send_Keypress_Keycode_Matrix.py
 * @brief Exercise supported keycode mappings to increase getUIKeyCode branch coverage.
 */
"""

import os
import time

from utils import send_jsonrpc_command, log_success, log_error, log_warning


# Keep in sync with HdmiCecSourceImplementation key constants.
SUPPORTED_KEYCODES = [
    0x41,  # VOLUME_UP
    0x42,  # VOLUME_DOWN
    0x43,  # MUTE
    0x01,  # UP
    0x02,  # DOWN
    0x03,  # LEFT
    0x04,  # RIGHT
    0x00,  # SELECT
    0x09,  # HOME
    0x0D,  # BACK
    0x20,  # NUMBER_0
    0x21,  # NUMBER_1
    0x22,  # NUMBER_2
    0x23,  # NUMBER_3
    0x24,  # NUMBER_4
    0x25,  # NUMBER_5
    0x26,  # NUMBER_6
    0x27,  # NUMBER_7
    0x28,  # NUMBER_8
    0x29,  # NUMBER_9
]


def _is_ok_response(resp):
    if not isinstance(resp, dict):
        return False
    if "error" in resp:
        return False
    result = resp.get("result", {})
    return isinstance(result, dict) and result.get("success") is True


def run_test():
    start_time = time.perf_counter()

    failures = []
    for key in SUPPORTED_KEYCODES:
        resp = send_jsonrpc_command(
            "org.rdk.HdmiCecSource.sendKeyPressEvent",
            params={"logicalAddress": 0, "keyCode": key},
            request_id=42000 + key,
            timeout=5,
        )
        if not _is_ok_response(resp):
            failures.append((key, resp))
        time.sleep(0.1)

    if failures:
        log_warning(f"TCID40 failures: {failures}")
        log_error("TCID40_Send_Keypress_Keycode_Matrix Failed ❌")
        return False

    elapsed = time.perf_counter() - start_time
    msg = "TCID40_Send_Keypress_Keycode_Matrix Passed ✅"
    if os.environ.get("HDMICEC_TIMING_ENABLED"):
        log_success(f"{msg} time consumed: {elapsed:.3f}s")
    else:
        log_success(msg)
    return True

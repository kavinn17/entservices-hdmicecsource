"""
/**
 * @file TCID42_Hotplug_KeyRelease_Event_Path.py
 * @brief Coverage-focused HDMI CEC Source testcase.
 *
 * @testcase TCID42_Hotplug_KeyRelease_Event_Path
 * @details Triggers hotplug and key release related event paths via Device_* YAML commands.
 */
"""

import json
import os
import time

from utils import (
    send_vcomponent_command,
    send_curl_command,
    HDMICEC_CMD_BASE,
    log_info,
    log_success,
    log_error,
    log_warning,
)
import HdmiCECSource_Curl as HdmiCecSourceApis


EVENT_YAMLS = [
    "Device_Bus_Status.yaml",
    "Device_User_Control_Pressed.yaml",
    "Device_User_Control_Released.yaml",
]


def _post(yaml_file):
    http_code, body = send_vcomponent_command(f"{HDMICEC_CMD_BASE}/{yaml_file}")
    log_info(f"  POST {yaml_file}: HTTP {http_code} {body}")
    return http_code == 200


def _get_enabled_ok():
    response = send_curl_command(HdmiCecSourceApis.get_enabled)
    if not response or response.startswith("< No response"):
        return False
    try:
        parsed = json.loads(response)
        result = parsed.get("result", {})
        return isinstance(result.get("enabled"), bool)
    except json.JSONDecodeError:
        return False


def run_test():
    start = time.perf_counter()
    log_info("TCID42 - Scenario: hotplug and key release event callback path")

    failed = []
    for yaml_file in EVENT_YAMLS:
        if not _post(yaml_file):
            failed.append(yaml_file)
        time.sleep(0.5)

    # Exercise explicit keypress API after event path stimulation.
    key_resp = send_curl_command(HdmiCecSourceApis.send_key_press_event)
    log_warning(f"  sendKeyPressEvent response: {key_resp}")

    if not _get_enabled_ok():
        log_error("  getEnabled failed after event path stimulation")
        return False

    if failed:
        log_warning(f"  failed YAML posts: {failed}")
        log_error("TCID42_Hotplug_KeyRelease_Event_Path Failed ❌")
        return False

    elapsed = time.perf_counter() - start
    msg = "TCID42_Hotplug_KeyRelease_Event_Path Passed ✅"
    if os.environ.get("HDMICEC_TIMING_ENABLED"):
        log_success(f"{msg} time consumed: {elapsed:.3f}s")
    else:
        log_success(msg)
    return True

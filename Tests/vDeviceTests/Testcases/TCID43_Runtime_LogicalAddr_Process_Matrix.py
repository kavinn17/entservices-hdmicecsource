"""
/**
 * @file TCID43_Runtime_LogicalAddr_Process_Matrix.py
 * @brief Coverage-focused HDMI CEC Source testcase.
 *
 * @testcase TCID43_Runtime_LogicalAddr_Process_Matrix
 * @details Reads the runtime emulated-device logical address from the vcomponent
 *          device-list info file and builds exact destination payloads for still-zero
 *          inbound processor handlers.
 *
 * @note Polling cannot be injected through the current vcomponent user_defined path
 *       because the backend rejects raw frames shorter than 2 bytes.
 */
"""

import json
import os
import re
import tempfile
import time
from pathlib import Path

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


DEVICE_LIST_INFO_PATH = Path("/tmp/hdmi_cec_device_list_info.txt")
SOURCE_NAME = "VTV"
SOURCE_NAME_CANDIDATES = {"VTV", "TV"}
SOURCE_TYPE_CANDIDATES = {"TV"}
SOURCE_ADDR_CANDIDATES = [0x0, 0x1, 0x5]
DEST_ADDR_FALLBACKS = [0x0, 0x1, 0x5, 0xF]
DISCOVERY_MAX_ATTEMPTS = 6
DISCOVERY_RETRY_SEC = 0.5
MAX_DISCOVERED_DEST_ADDRS = 8
ZERO_HIT_MESSAGES = [
    ("GiveOSDName", [0x46]),
    ("FeatureAbort", [0x00, 0x44, 0x04]),
    ("GetCECVersion", [0x9F]),
    ("ReportPowerStatus", [0x90, 0x00]),
    ("GiveDeviceVendorID", [0x8C]),
    ("UserControlPressed", [0x44, 0x41]),
    ("UserControlReleased", [0x45]),
    ("GiveDevicePowerStatus", [0x8F]),
    ("Abort", [0xFF]),
]


def _post_existing_yaml(yaml_name):
    http_code, body = send_vcomponent_command(f"{HDMICEC_CMD_BASE}/{yaml_name}")
    log_info(f"  POST {yaml_name}: HTTP {http_code} {body}")
    return http_code == 200


def _post_temp_payload(payload_bytes, description):
    yaml_text = "\n".join([
        "HdmiCec:",
        "  command: cec_message",
        f"  description: {description}",
        "  message:",
        "    user_defined: true",
        "    payload: [" + ", ".join(f'\"0x{b:02X}\"' for b in payload_bytes) + "]",
        "",
    ])

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        prefix="hdmicec_runtime_la_",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(yaml_text)
        tmp_path = tmp.name

    try:
        http_code, body = send_vcomponent_command(tmp_path)
        log_info(f"  POST {Path(tmp_path).name} ({description}): HTTP {http_code} {body}")
        return http_code == 200
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _read_runtime_logical_address():
    if not DEVICE_LIST_INFO_PATH.is_file():
        return None

    text = DEVICE_LIST_INFO_PATH.read_text(encoding="utf-8", errors="ignore")
    candidates = []
    for line in text.splitlines():
        if "Name:" not in line or "Logical-1:" not in line:
            continue

        name_match = re.search(r"Name:\s*([^,]+)", line)
        type_match = re.search(r"Type:\s*([^,]+)", line)
        logical_match = re.search(r"Logical-1:\s*(-?\d+)", line)
        if not logical_match:
            continue

        value = int(logical_match.group(1))
        if value < 0:
            continue

        name = name_match.group(1).strip() if name_match else ""
        dev_type = type_match.group(1).strip() if type_match else ""
        score = 0
        if name.upper() in SOURCE_NAME_CANDIDATES:
            score += 3
        if dev_type.upper() in SOURCE_TYPE_CANDIDATES:
            score += 2
        if "Active Source: 1" in line:
            score += 1

        candidates.append((score, value, name, dev_type))

    if candidates:
        best = sorted(candidates, key=lambda x: (x[0], x[1]), reverse=True)[0]
        log_info(
            f"  device-list best match: name={best[2]} type={best[3]} logical={best[1]} score={best[0]}"
        )
        return best[1]

    return None


def _read_runtime_logical_addresses():
    if not DEVICE_LIST_INFO_PATH.is_file():
        return []

    text = DEVICE_LIST_INFO_PATH.read_text(encoding="utf-8", errors="ignore")
    candidates = []
    for line in text.splitlines():
        if "Name:" not in line or "Logical-1:" not in line:
            continue

        name_match = re.search(r"Name:\s*([^,]+)", line)
        type_match = re.search(r"Type:\s*([^,]+)", line)
        logical_match = re.search(r"Logical-1:\s*(-?\d+)", line)
        if not logical_match:
            continue

        value = int(logical_match.group(1))
        if value < 0 or value > 15:
            continue

        name = name_match.group(1).strip() if name_match else ""
        dev_type = type_match.group(1).strip() if type_match else ""
        score = 0
        if name.upper() in SOURCE_NAME_CANDIDATES:
            score += 3
        if dev_type.upper() in SOURCE_TYPE_CANDIDATES:
            score += 2
        if "Active Source: 1" in line:
            score += 1
        candidates.append((score, value))

    if not candidates:
        return []

    ordered = []
    seen = set()
    for score, value in sorted(candidates, key=lambda x: (x[0], x[1]), reverse=True):
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
        if len(ordered) >= MAX_DISCOVERED_DEST_ADDRS:
            break
    return ordered


def _read_logical_from_get_device_list():
    response = send_curl_command(HdmiCecSourceApis.get_device_list)
    if not response or response.startswith("< No response"):
        return None

    try:
        body = json.loads(response)
        result = body.get("result", {})
        device_list = result.get("deviceList", [])
        if not isinstance(device_list, list):
            return None

        candidates = []
        for item in device_list:
            if not isinstance(item, dict):
                continue
            logical = item.get("logicalAddress")
            if not isinstance(logical, int) or logical < 0:
                continue

            name = str(item.get("osdName") or item.get("name") or "").strip()
            dev_type = str(item.get("deviceType") or "").strip()
            score = 0
            if name.upper() in SOURCE_NAME_CANDIDATES:
                score += 3
            if dev_type.upper() in SOURCE_TYPE_CANDIDATES:
                score += 2
            if item.get("activeSource") is True:
                score += 1
            candidates.append((score, logical, name, dev_type))

        if candidates:
            best = sorted(candidates, key=lambda x: (x[0], x[1]), reverse=True)[0]
            log_info(
                f"  getDeviceList best match: name={best[2]} type={best[3]} logical={best[1]} score={best[0]}"
            )
            return best[1]
    except json.JSONDecodeError:
        return None

    return None


def _read_logicals_from_get_device_list():
    response = send_curl_command(HdmiCecSourceApis.get_device_list)
    if not response or response.startswith("< No response"):
        return []

    try:
        body = json.loads(response)
        result = body.get("result", {})
        device_list = result.get("deviceList", [])
        if not isinstance(device_list, list):
            return []

        candidates = []
        for item in device_list:
            if not isinstance(item, dict):
                continue
            logical = item.get("logicalAddress")
            if not isinstance(logical, int) or logical < 0 or logical > 15:
                continue

            name = str(item.get("osdName") or item.get("name") or "").strip()
            dev_type = str(item.get("deviceType") or "").strip()
            score = 0
            if name.upper() in SOURCE_NAME_CANDIDATES:
                score += 3
            if dev_type.upper() in SOURCE_TYPE_CANDIDATES:
                score += 2
            if item.get("activeSource") is True:
                score += 1
            candidates.append((score, logical))

        if not candidates:
            return []

        ordered = []
        seen = set()
        for score, logical in sorted(candidates, key=lambda x: (x[0], x[1]), reverse=True):
            if logical in seen:
                continue
            seen.add(logical)
            ordered.append(logical)
            if len(ordered) >= MAX_DISCOVERED_DEST_ADDRS:
                break
        return ordered
    except json.JSONDecodeError:
        return []


def _discover_runtime_logical_addresses():
    for attempt in range(1, DISCOVERY_MAX_ATTEMPTS + 1):
        logical_addrs = _read_runtime_logical_addresses()
        if logical_addrs:
            return logical_addrs

        if attempt in (2, 4):
            _post_existing_yaml("Device_Print.yaml")

        time.sleep(DISCOVERY_RETRY_SEC)

    logical_addrs = _read_logicals_from_get_device_list()
    if logical_addrs:
        return logical_addrs

    one_addr = _read_logical_from_get_device_list()
    if one_addr is not None:
        return [one_addr]

    return []


def _api_ok():
    response = send_curl_command(HdmiCecSourceApis.get_device_list)
    if not response or response.startswith("< No response"):
        return False
    try:
        body = json.loads(response)
        return isinstance(body, dict) and "error" not in body and "result" in body
    except json.JSONDecodeError:
        return False


def run_test():
    start = time.perf_counter()
    log_info("TCID43 - Scenario: runtime logical-address targeted process matrix")

    if not _post_existing_yaml("Device_Print.yaml"):
        log_error("  failed to request vcomponent device-list dump")
        return False
    time.sleep(1)

    discovered_addrs = _discover_runtime_logical_addresses()
    log_warning(f"  runtime discovered destination logical addresses: {discovered_addrs}")
    if not discovered_addrs:
        log_warning(
            "  unable to discover runtime logical address from /tmp/hdmi_cec_device_list_info.txt; "
            "using fallback destination set"
        )
        discovered_addrs = list(DEST_ADDR_FALLBACKS)

    # Always include broadcast to maximize decoder-path stimulation for commands
    # that are accepted as broadcast on the CEC bus.
    dest_addrs = []
    for addr in list(discovered_addrs) + [0xF]:
        if isinstance(addr, int) and 0 <= addr <= 15 and addr not in dest_addrs:
            dest_addrs.append(addr)

    if not _api_ok():
        log_error("  pre-check API health failed")
        return False

    failures = []
    for dst in dest_addrs:
        for src in SOURCE_ADDR_CANDIDATES:
            header = ((src & 0x0F) << 4) | (dst & 0x0F)
            for name, tail in ZERO_HIT_MESSAGES:
                payload = [header] + tail
                if not _post_temp_payload(payload, f"Inject {name} src={src} dst={dst}"):
                    failures.append(f"{name}[src={src},dst={dst}]")
                time.sleep(0.35)

    # Polling cannot be sent here because backend rejects user_defined payloads shorter than 2 bytes.
    log_warning("  Polling omitted: vcomponent backend rejects raw user_defined frames with <2 bytes")

    if not _api_ok():
        log_error("  post-check API health failed")
        return False

    if failures:
        log_warning(f"  failed injected payload posts: {failures}")
        log_error("TCID43_Runtime_LogicalAddr_Process_Matrix Failed ❌")
        return False

    elapsed = time.perf_counter() - start
    msg = "TCID43_Runtime_LogicalAddr_Process_Matrix Passed ✅"
    if os.environ.get("HDMICEC_TIMING_ENABLED"):
        log_success(f"{msg} time consumed: {elapsed:.3f}s")
    else:
        log_success(msg)
    return True

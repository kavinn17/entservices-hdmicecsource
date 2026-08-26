"""
/**
 * @file SuitManager.py
 * @brief SuitManager.py
 *
 * @testcase SuitManager
 * @details Orchestrates the HDMI CEC Source L2 test suite by dynamically loading and executing
 *          test case modules, activating the required RDK plugin via JSON-RPC, and reporting
 *          per-test pass/fail results with summary statistics.
 *
 * @precondition
 *  - WPEFramework is running and reachable at the configured JSON-RPC endpoint.
 *  - The org.rdk.HdmiCecSource plugin is available for activation.
 *  - All test case modules listed in SUITES are present under the Testcases/ directory.
 *
 * @dependencies
 *  - utils.py
 *  - HdmiCECSource_Curl.py
 *  - Testcases/*.py
 *
 * @expected_result
 *  - All registered test cases are executed in order and results are logged.
 *
 * @pass_criteria
 *  - Each test case module's run_test() returns True and is reported as PASSED.
 *
 * @failure_criteria
 *  - Any test case returns False, raises an exception, or the plugin fails to activate.
 */
"""

import importlib
import io
import sys
import time
from pathlib import Path
import os
import subprocess

from utils import log_error, log_info, log_success, send_jsonrpc_command, WPEFRAMEWORK_JSONRPC_URL


BASE_DIR = Path(__file__).resolve().parent
SUITES = {
    "hdmicecsource": {
        "banner": "******************** L2 SUITE - RDK - HDMI CEC SOURCE ****************************",
        "module_dir": BASE_DIR / "Testcases",
        "tests": [
            "TCID01_Send_Standby_Message",
            "TCID02_Get_Devicelist",
            "TCID03_Get_Enabled_Status",
            "TCID04_Get_OTP_Enabled",
            "TCID05_Get_Vendor_ID",
            "TCID06_Perform_OTP_Action",
            "TCID07_Send_Keypress_Event",
            "TCID08_Set_Enabled_False",
            "TCID09_Set_Enabled_True",
            "TCID10_Set_OTP_Name",
            "TCID11_Set_OTP_Enabled_False",
            "TCID12_Set_OTP_Enabled_True",
            "TCID13_Set_Vendor_ID",
            "TCID14_Verify_Vendor_ID_Readback",
            "TCID15_Get_OSD_Name",
            "TCID16_OTP_After_Powerstatus_Reporting",
            "TCID17_Menu_Language_CECversion_Flow",
            "TCID18_Active_Source_Routing_View_ON_Flow",
            "TCID19_Standby_OTP_Powerstatus_Flow",
            "TCID20_Standby_OTP_Userdef_CEC",
            "TCID21_Add_Remove_Device_Vcomponent",
            "TCID22_Verify_Devicelist_CEC_Disabled",
            "TCID23_Disable_CEC_Verify_Enabled",
            "TCID24_Standby_Userdef_Busstatus",
            "TCID25_Add_Network_Verify_Discovery",
            "TCID26_Standby_Then_OTP_Wakeup",
            "TCID27_Active_Source_Transition_After_OTP",
            "TCID28_Invalid_VendorID_Nochange",
            "TCID29_Repeated_Disable_Idempotent",
            "TCID30_Repeated_Enable_Idempotent",
            "TCID31_Invalid_OTP_Setnochange",
            "TCID32_Invalid_OSD_Setnochange",
            "TCID33_Process_Yaml_Health_Check",
            "TCID34_Invalid_Keypress_LogicalAddress",
            "TCID35_Invalid_Keypress_UnsupportedKey",
            "TCID36_Set_Empty_VendorID_Fails",
            "TCID37_Disabled_CEC_Negative_Actions",
            "TCID38_Set_VendorID_InvalidFormat_Defaults",
            "TCID39_Set_VendorID_OutOfRange_Defaults",
            "TCID40_Send_Keypress_Keycode_Matrix",
            "TCID41_Send_Keypress_When_Disabled",
            "TCID42_Hotplug_KeyRelease_Event_Path",
            "TCID43_Runtime_LogicalAddr_Process_Matrix",
           //"TCID44_Explicit_Plugin_Deactivate_Recover",
        ],
    },
}

# Maps test suite names to their corresponding RDK plugin callsigns for activation
SUITE_PLUGIN_CALLSIGNS = {
    "hdmicecsource": "org.rdk.HdmiCecSource",
}

SUITE_INIT_MODULES = {
    "hdmicecsource": "Init_Devicelist_Populate",
}

SUITE_PROFILE_SCRIPTS = {
    "hdmicecsource": "Profile.sh",
}

SUITE_RDK_PROFILES = {
    "hdmicecsource": "STB",
}


def normalize_suite_name(raw_name):
    return raw_name.strip().replace("_", "").replace("-", "").lower()


def load_test_cases(suite_name):
    suite_config = SUITES[suite_name]
    module_dir = str(suite_config["module_dir"])

    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)

    test_cases = []
    for module_name in suite_config["tests"]:
        module = importlib.import_module(module_name)
        test_cases.append((module_name, module.run_test))

    return suite_config["banner"], test_cases


def activate_plugin_via_curl(callsign):
    response = send_jsonrpc_command(
        "Controller.1.activate",
        params={"callsign": callsign},
        request_id=1234567890,
    )
    if not response:
        return False
    if "error" in response:
        return False
    return "result" in response


def framework_ready():
    # A JSON-RPC response (result or error) means the framework endpoint is up.
    response = send_jsonrpc_command("Controller.1.status", request_id=1234567801)
    return isinstance(response, dict)


def plugin_api_ready(callsign):
    response = send_jsonrpc_command(f"{callsign}.getEnabled", request_id=1234567802)
    if not isinstance(response, dict):
        return False
    if "error" in response:
        return False
    return "result" in response


def wait_for_framework_ready(timeout_seconds=60, poll_interval=2):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if framework_ready():
            return True
        time.sleep(poll_interval)
    return False


def activate_plugin_with_retry(callsign, retries=25, delay_seconds=2):
    # If the plugin is already responsive, no need to activate again.
    if plugin_api_ready(callsign):
        log_info(f"Plugin already responsive: {callsign}")
        return True

    activate_methods = [
        "Controller.1.activate",
        "Controller.activate",
    ]

    for attempt in range(1, retries + 1):
        activated = False

        for method in activate_methods:
            response = send_jsonrpc_command(
                method,
                params={"callsign": callsign},
                request_id=1234567890 + attempt,
            )

            if isinstance(response, dict) and "error" not in response and "result" in response:
                activated = True
                break

            if isinstance(response, dict) and "error" in response:
                log_info(
                    f"Activation response via {method} attempt {attempt}: {response.get('error')}"
                )

        # Some builds can return non-success for activate while plugin becomes ready shortly after.
        if activated:
            if plugin_api_ready(callsign):
                return True

        if plugin_api_ready(callsign):
            log_info(f"Plugin became responsive after activation attempt {attempt}: {callsign}")
            return True

        log_info(f"Activation retry {attempt}/{retries} for {callsign} did not succeed yet")
        time.sleep(delay_seconds)

    return plugin_api_ready(callsign)


def run_suite_init(suite_name):
    module_name = SUITE_INIT_MODULES.get(suite_name)
    if not module_name:
        return True

    if BASE_DIR.as_posix() not in sys.path:
        sys.path.insert(0, str(BASE_DIR))

    try:
        module = importlib.import_module(module_name)
    except Exception as exc:
        log_error(f"Init module import failed: {module_name} ({exc})")
        return False

    run_fn = getattr(module, "run_test", None)
    if not callable(run_fn):
        log_error(f"Init module missing run_test(): {module_name}")
        return False

    log_info(f"Running suite initialization: {module_name}.run_test()")
    try:
        ok = bool(run_fn())
    except Exception as exc:
        log_error(f"Suite initialization threw exception: {exc}")
        return False

    if ok:
        log_success("Suite initialization completed successfully")
    else:
        log_error("Suite initialization failed")
    return ok


def set_rdk_profile_via_script(suite_name, profile):
    script_name = SUITE_PROFILE_SCRIPTS.get(suite_name, "Profile.sh")
    script_path = BASE_DIR / script_name
    if not script_path.exists():
        log_error(f"Profile script not found: {script_path}")
        return False

    commands = [
        ["sh", str(script_path), profile],
        ["bash", str(script_path), profile],
    ]

    last_error = None
    for cmd in commands:
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
        except FileNotFoundError as exc:
            last_error = exc
            continue

        stdout_text = (proc.stdout or "").strip()
        stderr_text = (proc.stderr or "").strip()

        if proc.returncode == 0:
            if stdout_text:
                log_info(stdout_text)
            if stderr_text:
                log_info(stderr_text)
            return True

        log_error(f"Profile command failed ({' '.join(cmd)}), rc={proc.returncode}")
        if stdout_text:
            log_error(stdout_text)
        if stderr_text:
            log_error(stderr_text)
        return False

    if last_error:
        log_error(f"Unable to run profile script with shell interpreter: {last_error}")
    else:
        log_error("Unable to run profile script with available shell interpreter")
    return False


def run_suite(suite_name):
    banner, test_cases = load_test_cases(suite_name)
    print(banner)

    expected_count = 44
    if len(test_cases) != expected_count:
        log_error(
            f"Expected {expected_count} testcases, but found {len(test_cases)} in suite '{suite_name}'"
        )
        return False
    log_info(f"Running exactly {expected_count} testcases for suite '{suite_name}'")

    # Flow requirement: profile is always set from suite defaults (STB for hdmicecsource).
    profile = SUITE_RDK_PROFILES.get(suite_name)
    if profile:
        profile = profile.strip().upper()
        log_info(f"Setting RDK profile to '{profile}' via Profile.sh")
        if not set_rdk_profile_via_script(suite_name, profile):
            log_error("Aborting suite because RDK profile setup failed.")
            return False
        log_success(f"RDK profile set to {profile}")

    auto_activate = os.environ.get("AUTO_ACTIVATE_PLUGINS", "1").lower() not in ("0", "false", "no")
    callsign = SUITE_PLUGIN_CALLSIGNS.get(suite_name)
    if auto_activate and callsign:
        log_info(f"Waiting for framework JSON-RPC readiness at {WPEFRAMEWORK_JSONRPC_URL}")
        if wait_for_framework_ready(timeout_seconds=60, poll_interval=2):
            log_success("WPEFramework JSON-RPC endpoint is ready")
        else:
            log_error("WPEFramework JSON-RPC endpoint is not ready after restart window")
            return False

        log_info(f"Auto-activating plugin '{callsign}' via curl JSON-RPC at {WPEFRAMEWORK_JSONRPC_URL}")
        if activate_plugin_with_retry(callsign, retries=25, delay_seconds=2):
            log_success(f"Plugin activated: {callsign}")
            log_info("Waiting 4s for plugin to fully initialise...")
            time.sleep(4)
        else:
            log_error(f"Plugin activation failed: {callsign}")
            log_error("Check JSON-RPC endpoint reachability and plugin availability before running tests.")
            return False

    if not run_suite_init(suite_name):
        log_error("Aborting suite because initialization did not complete successfully.")
        return False

    passed = 0
    failed = 0
    failed_cases = []
    original_stdout = sys.stdout

    for tc_name, tc_fn in test_cases:
        log_info(f"\n{'='*60}")
        log_info(f"Running: {tc_name}")
        log_info(f"{'='*60}")
        captured = io.StringIO()
        sys.stdout = captured
        try:
            result = tc_fn()
        except Exception as exc:
            result = False
            print(f"EXCEPTION in {tc_name}: {exc}")
        finally:
            sys.stdout = original_stdout

        output = captured.getvalue()
        print(output, end="")

        if result:
            passed += 1
            log_success(f"[PASS] {tc_name}")
        else:
            failed += 1
            failed_cases.append(tc_name)
            log_error(f"[FAIL] {tc_name}")

        time.sleep(1)

    total = passed + failed
    log_info(f"\n{'='*60}")
    log_info(f"Suite Summary: total={total}, passed={passed}, failed={failed}")
    if failed_cases:
        log_error(f"Failed cases: {failed_cases}")
    log_info(f"{'='*60}")

    return failed == 0


if __name__ == "__main__":
    # Only support two invocation forms:
    #   python3 SuitManager.py
    #   python3 SuitManager.py -time
    argv = sys.argv[1:]
    if len(argv) == 0:
        timing_enabled = False
    elif len(argv) == 1 and argv[0] == "-time":
        timing_enabled = True
    else:
        print("usage: SuitManager.py [-time]", file=sys.stderr)
        print("SuitManager.py: error: only '-time' is supported", file=sys.stderr)
        sys.exit(2)

    # Set environment variable for timing mode
    if timing_enabled:
        os.environ["HDMICEC_TIMING_ENABLED"] = "1"

    ok = run_suite("hdmicecsource")
    sys.exit(0 if ok else 1)

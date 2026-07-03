To execute the HDMI CEC Source L2 suite inside QEMU/server:

cd /tmp
git clone git@github.com:rdkcentral/entservices-hdmicecsource.git
cd entservices-hdmicecsource/Tests/vDeviceTests

EXECUTION:
- without timing output: python3 SuitManager.py
- with timing output: python3 SuitManager.py -time

Current suite behavior:
- Runs the 44 registered HDMI CEC Source testcases.
- Sets the RDK profile to STB before suite execution using Profile.sh.
- Waits for WPEFramework JSON-RPC readiness.
- Activates org.rdk.HdmiCecSource automatically.
- Runs Init_Devicelist_Populate before testcase execution.
- Generates coverage automatically after testcase execution completes.

Coverage behavior:
- Coverage is generated in the same runtime when SuitManager.py completes the testcases.
- The coverage report script is hdmicecsource-gcov-report.sh.
- The coverage script executes from the vDeviceTests directory.
- Default coverage output on server is:
	/tmp/hdmicecsource-coverage

Expected coverage artifacts:
- /tmp/hdmicecsource-coverage/coverage.info
- /tmp/hdmicecsource-coverage/plugin.info
- /tmp/hdmicecsource-coverage/ccec.info
- /tmp/hdmicecsource-coverage/html/index.html

Default actions:
- hdmicecsource -> Controller.1.activate(callsign=org.rdk.HdmiCecSource)
- Init_Devicelist_Populate is executed automatically.
- Coverage cleanup/restart/report flow is executed automatically.

Disable default activation only if needed:
- export AUTO_ACTIVATE_PLUGINS=0

If the testcases fail with "connection refused", configure endpoint host/ports before running.

Defaults used by the tests:
- MW JSON-RPC: http://127.0.0.1:9998/jsonrpc
- vComponent API: http://127.0.0.1:8080/api/postKVP

Useful overrides:
- TARGET_HOST (applies to both endpoints)
- JSONRPC_PORT
- VCOMPONENT_PORT
- WPEFRAMEWORK_JSONRPC_URL (full URL, highest priority)
- VCOMPONENT_API_URL (full URL, highest priority)

Examples:

# when running directly inside QEMU guest (services on localhost)
python3 SuitManager.py

# when running directly inside QEMU guest with timing enabled
python3 SuitManager.py -time

# when running from host against QEMU target IP
export TARGET_HOST=192.168.1.50
export JSONRPC_PORT=9998
export VCOMPONENT_PORT=8080
python3 SuitManager.py

# full URL override form
export WPEFRAMEWORK_JSONRPC_URL=http://192.168.1.50:9998/jsonrpc
export VCOMPONENT_API_URL=http://192.168.1.50:8080/api/postKVP
python3 SuitManager.py

Troubleshooting:
- If you see connection errors, verify WPEFramework JSON-RPC and the vComponent API are reachable using the endpoint overrides above.
- If coverage generation fails, verify gcov/lcov runtime dependencies are installed in the image.
- If CCEC coverage shows no data, verify CCEC gcda files are being produced under /tmp/gcov during runtime.

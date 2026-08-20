#!/bin/bash
#
# If not stated otherwise in this file or this component's LICENSE
# file the following copyright and licenses apply:
#
# Copyright 2026 RDK Management
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -x
set -e
##############################
GITHUB_WORKSPACE="${PWD}"
ls -la ${GITHUB_WORKSPACE}
cd ${GITHUB_WORKSPACE}

# # ############################# 
#1. Install Dependencies and packages

apt update
apt install -y libcurl4-openssl-dev valgrind lcov clang libsystemd-dev libboost-all-dev curl libunwind-dev libdrm-dev patchelf
pip install jsonref

###########################################
# Clone the required repositories


git clone --branch  R4.4.3 https://github.com/rdkcentral/ThunderTools.git

git clone --branch R4.4.1 https://github.com/rdkcentral/Thunder.git

git clone --branch 4.0.8 https://github.com/rdkcentral/entservices-apis.git

cd ..
git clone --branch develop https://github.com/rdkcentral/entservices-helpers.git
cd "$GITHUB_WORKSPACE"

git clone --branch 1.0.17 https://github.com/rdkcentral/entservices-testframework.git

# support/AIDL matches the guest's shipped libRCEC/libRCECOSHal ABI (has the AIDL changes)
git clone --branch support/AIDL --depth 1 https://github.com/rdkcentral/hdmicec.git
git clone --depth 1 https://github.com/rdkcentral/iarmbus.git
git clone --branch 6.0.0 --depth 1 https://github.com/rdkcentral/rdk-halif-device_settings.git
git clone --branch develop --depth 1 https://github.com/rdkcentral/devicesettings.git devicesettings-src

############################
# Build Thunder-Tools
echo "======================================================================================"
echo "buliding thunderTools"
cd ThunderTools
patch -p1 < $GITHUB_WORKSPACE/entservices-testframework/patches/00010-R4.4-Add-support-for-project-dir.patch
cd -


cmake -G Ninja -S ThunderTools -B build/ThunderTools \
    -DEXCEPTIONS_ENABLE=ON \
    -DCMAKE_INSTALL_PREFIX="$GITHUB_WORKSPACE/install/usr" \
    -DCMAKE_MODULE_PATH="$GITHUB_WORKSPACE/install/tools/cmake" \
    -DGENERIC_CMAKE_MODULE_PATH="$GITHUB_WORKSPACE/install/tools/cmake" \

cmake --build build/ThunderTools --target install


############################
# Build Thunder
echo "======================================================================================"
echo "buliding thunder"

cd Thunder
patch -p1 < $GITHUB_WORKSPACE/entservices-testframework/patches/Use_Legact_Alt_Based_On_ThunderTools_R4.4.3.patch
patch -p1 < $GITHUB_WORKSPACE/entservices-testframework/patches/error_code_R4_4.patch
patch -p1 < $GITHUB_WORKSPACE/entservices-testframework/patches/1004-Add-support-for-project-dir.patch
patch -p1 < $GITHUB_WORKSPACE/entservices-testframework/patches/RDKEMW-733-Add-ENTOS-IDS.patch
cd -

cmake -G Ninja -S Thunder -B build/Thunder \
    -DMESSAGING=ON \
    -DCMAKE_INSTALL_PREFIX="$GITHUB_WORKSPACE/install/usr" \
    -DCMAKE_MODULE_PATH="$GITHUB_WORKSPACE/install/tools/cmake" \
    -DGENERIC_CMAKE_MODULE_PATH="$GITHUB_WORKSPACE/install/tools/cmake" \
    -DBUILD_TYPE=Debug \
    -DBINDING=127.0.0.1 \
    -DPORT=55555 \
    -DEXCEPTIONS_ENABLE=ON \

cmake --build build/Thunder --target install

# Fix Thunder library SONAMEs to version 4 (matching the QEMU guest image).
# The R4.4.1 source + test-framework patches produce SOVERSION=1, but the
# guest ships .so.4; without this the plugin records NEEDED .so.1 and segfaults.
THUNDER_SOVERSION=4
INSTALL_LIB_DIR="$GITHUB_WORKSPACE/install/usr/lib"
for lib in WPEFrameworkCore WPEFrameworkPlugins WPEFrameworkMessaging WPEFrameworkWebSocket WPEFrameworkCOM; do
    real_file="$(find "$INSTALL_LIB_DIR" -maxdepth 1 -name "lib${lib}.so*" -type f ! -name "*.so" 2>/dev/null | head -1)"
    [[ -n "$real_file" ]] || continue
    patchelf --set-soname "lib${lib}.so.${THUNDER_SOVERSION}" "$real_file"
    ln -sf "$(basename "$real_file")" "$INSTALL_LIB_DIR/lib${lib}.so.${THUNDER_SOVERSION}"
    ln -sf "lib${lib}.so.${THUNDER_SOVERSION}" "$INSTALL_LIB_DIR/lib${lib}.so"
    echo "Fixed SONAME: lib${lib}.so -> .so.${THUNDER_SOVERSION}"
done


############################
# Build entservices-apis
echo "======================================================================================"
echo "buliding entservices-apis"
cd entservices-apis
rm -rf jsonrpc/DTV.json
cd ..

cmake -G Ninja -S entservices-apis  -B build/entservices-apis \
    -DEXCEPTIONS_ENABLE=ON \
    -DCMAKE_INSTALL_PREFIX="$GITHUB_WORKSPACE/install/usr" \
    -DCMAKE_MODULE_PATH="$GITHUB_WORKSPACE/install/tools/cmake" \

cmake --build build/entservices-apis --target install

############################
# generating minimal mock headers
cd $GITHUB_WORKSPACE/entservices-testframework/Tests
mkdir -p headers
cd headers
touch secure_wrapper.h
touch wpa_ctrl.h
touch rdk_logger_milestone.h
mkdir -p rdk/iarmbus
touch rdk/iarmbus/libIARM.h
touch rdk/iarmbus/libIBus.h
touch iarm.h
cd $GITHUB_WORKSPACE
#############################
# Build entservices-helpers
echo "======================================================================================"
echo "building entservices-helpers"
cmake -G Ninja -S ../entservices-helpers -B build/entservices-helpers \
    -DEXCEPTIONS_ENABLE=ON \
    -DCMAKE_INSTALL_PREFIX="$GITHUB_WORKSPACE/install/usr" \
    -DCMAKE_MODULE_PATH="$GITHUB_WORKSPACE/install/tools/cmake" \
    "-DCMAKE_CXX_FLAGS=-I$GITHUB_WORKSPACE/entservices-testframework/Tests/mocks -I$GITHUB_WORKSPACE/entservices-testframework/Tests/headers -I$GITHUB_WORKSPACE/entservices-testframework/Tests/headers/rdk/iarmbus -include $GITHUB_WORKSPACE/entservices-testframework/Tests/mocks/Iarm.h "
cmake --build build/entservices-helpers --target install

############################
# Install real DS/CEC/IARM headers and create stub libraries
echo "======================================================================================"
echo "Installing real headers from cloned source repos"
INSTALL_INC="$GITHUB_WORKSPACE/install/usr/include"
INSTALL_LIB="$GITHUB_WORKSPACE/install/usr/lib"

# --- DS C++ wrapper headers (full tree to resolve internal chain includes) ---
mkdir -p "$INSTALL_INC/rdk/ds"
cp "$GITHUB_WORKSPACE/devicesettings-src/ds/include/"*.hpp "$INSTALL_INC/rdk/ds/"
cp "$GITHUB_WORKSPACE/devicesettings-src/ds/include/"*.h   "$INSTALL_INC/rdk/ds/" 2>/dev/null || true

# --- DS HAL C headers (dsTypes.h, dsError.h, dsDisplay.h, dsAVDTypes.h, …) ---
# These are the chain deps that the C++ wrappers pull in transitively.
mkdir -p "$INSTALL_INC/rdk/halif/ds-hal"
cp "$GITHUB_WORKSPACE/rdk-halif-device_settings/include/"*.h "$INSTALL_INC/rdk/halif/ds-hal/"

# --- CEC headers (full ccec + osal include trees) ---
# Connection.hpp → CECFrame.hpp → Operands.hpp → Header.hpp → OpCode.hpp, etc.
# Copying the full tree ensures all internal chain dependencies resolve.
mkdir -p "$INSTALL_INC/ccec/include"
cp -r "$GITHUB_WORKSPACE/hdmicec/ccec/include/ccec" "$INSTALL_INC/ccec/include/"
mkdir -p "$INSTALL_INC/osal/include"
cp -r "$GITHUB_WORKSPACE/hdmicec/osal/include/osal" "$INSTALL_INC/osal/include/"

# --- IARM headers ---
mkdir -p "$INSTALL_INC/rdk/iarmbus"
IARM_HDR=$(find "$GITHUB_WORKSPACE/iarmbus" -name "libIARM.h" -type f 2>/dev/null | head -1)
if [ -n "$IARM_HDR" ]; then
    IARM_DIR=$(dirname "$IARM_HDR")
    cp "$IARM_DIR"/libIARM.h "$INSTALL_INC/rdk/iarmbus/"
    cp "$IARM_DIR"/libIBus.h "$INSTALL_INC/rdk/iarmbus/" 2>/dev/null || true
else
    echo "WARNING: libIARM.h not found in iarmbus clone" >&2
fi

# --- Minimal telemetry header (function declaration only) ---
cat > "$INSTALL_INC/telemetry_busmessage_sender.h" << 'TELEOF'
#pragma once
#ifdef __cplusplus
extern "C" {
#endif
void t2_event_s(const char* marker, const char* value);
#ifdef __cplusplus
}
#endif
TELEOF

# --- Stub shared libraries (link-time only; MUST NOT be deployed to guest) ---
# Placed in a subdirectory so the workflow runtime-lib collector never picks them up.
# Sonames MUST match the versioned names on the QEMU guest image so the plugin's
# NEEDED entries resolve at runtime (e.g. libRCEC.so.0, not libRCEC.so).
# Stubs export the real function symbols the plugin code references, so the
# linker's --as-needed keeps the library in the NEEDED list.
STUB_LIB="$INSTALL_LIB/build-stubs"
mkdir -p "$STUB_LIB"

# IARMBus stub — exports symbols used via UtilsIarm.h
cat > /tmp/stub_IARMBus.c << 'EOF'
#include <stddef.h>
typedef int IARM_Result_t;
typedef void* IARM_EventHandler_t;
IARM_Result_t IARM_Bus_Init(const char *n) { return 0; }
IARM_Result_t IARM_Bus_Connect(void) { return 0; }
IARM_Result_t IARM_Bus_IsConnected(const char *n, int *c) { if(c) *c=1; return 0; }
IARM_Result_t IARM_Bus_RegisterEventHandler(const char *o, int e, void *h) { return 0; }
IARM_Result_t IARM_Bus_UnRegisterEventHandler(const char *o, int e) { return 0; }
IARM_Result_t IARM_Bus_Call(const char *o, const char *m, void *a, size_t s) { return 0; }
EOF
gcc -shared -o "$STUB_LIB/libIARMBus.so" /tmp/stub_IARMBus.c -Wl,-soname,libIARMBus.so.0

# telemetry stub — exports t2_event_s used when ENABLE_TELEMETRY_LOGGING is set
cat > /tmp/stub_telemetry.c << 'EOF'
void t2_event_s(const char* marker, const char* value) { (void)marker; (void)value; }
void t2_event_d(const char* marker, int value) { (void)marker; (void)value; }
EOF
gcc -shared -o "$STUB_LIB/libtelemetry_msgsender.so" /tmp/stub_telemetry.c -Wl,-soname,libtelemetry_msgsender.so.0

# CEC/OSAL/DS stubs — minimal symbols for link resolution
declare -A STUB_SOVERSIONS=(
    [RCEC]=0
    [RCECOSHal]=0
)
for lib in ds dshalcli RCEC RCECOSHal; do
    sover="${STUB_SOVERSIONS[$lib]:-}"
    if [[ -n "$sover" ]]; then
        soname="lib${lib}.so.${sover}"
    else
        soname="lib${lib}.so"
    fi
    echo "void __${lib}_stub(void){}" | gcc -shared -o "$STUB_LIB/lib${lib}.so" \
        -x c - -Wl,-soname,"$soname"
done

echo "Real headers and stub libraries installed."
echo "======================================================================================"

# Verify critical headers landed correctly
echo "--- Header install verification ---"
for h in rdk/ds/manager.hpp rdk/halif/ds-hal/dsTypes.h rdk/iarmbus/libIARM.h \
         ccec/include/ccec/Connection.hpp osal/include/osal/Mutex.hpp; do
    [ -f "$INSTALL_INC/${h}" ] && echo "  OK   ${h}" || echo "  MISS ${h}" >&2
done
echo "--- Stub library verification ---"
ls -1 "$INSTALL_LIB/build-stubs"/lib{ds,dshalcli,RCEC,RCECOSHal,IARMBus,telemetry_msgsender}.so 2>&1
echo "---"

ls -la ${GITHUB_WORKSPACE}

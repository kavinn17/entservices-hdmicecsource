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
#
# Coverage build for the real entservices-hdmicecsource plugin .so (L3/vDeviceTests).
# No L1 unit-test mocks or test-framework headers are included so the resulting
# shared libraries can be deployed directly into the QEMU image.

set -x
set -e

GITHUB_WORKSPACE="${PWD}"
ls -la "${GITHUB_WORKSPACE}"

echo "======================================================================================"
echo "Building entservices-hdmicecsource with coverage flags (L3/vDeviceTests)"

cd "${GITHUB_WORKSPACE}"

# C++17 ensures static constexpr members are implicitly inline, avoiding
# undefined symbol errors if the QEMU image ships a different Thunder ABI.
sed -i 's/CXX_STANDARD 11/CXX_STANDARD 17/g' plugin/CMakeLists.txt

# Verify real headers were installed by build_dependencies.sh
echo "--- Installed header verification ---"
for h in rdk/ds/manager.hpp rdk/halif/ds-hal/dsTypes.h rdk/iarmbus/libIARM.h \
         ccec/include/ccec/Connection.hpp osal/include/osal/Mutex.hpp \
         telemetry_busmessage_sender.h; do
    if [ -f "${GITHUB_WORKSPACE}/install/usr/include/${h}" ]; then
        echo "  OK   ${h}"
    else
        echo "  MISS ${h}" >&2
    fi
done
echo "---"

# Pre-seed all find_path/find_library cache variables so the Find modules
# don't rely on auto-discovery. Set optional dirs (DSRPC, IARMRECEIVER) to
# a valid path so their NOTFOUND values don't poison include dirs lists.
INCPFX="${GITHUB_WORKSPACE}/install/usr/include"
LIBPFX="${GITHUB_WORKSPACE}/install/usr/lib/build-stubs"

cmake -G Ninja -S "${GITHUB_WORKSPACE}" -B build/entservices-hdmicecsource \
  -DUSE_THUNDER_R4=ON \
  -DCMAKE_INSTALL_PREFIX="${GITHUB_WORKSPACE}/install/usr" \
  -DCMAKE_MODULE_PATH="${GITHUB_WORKSPACE}/install/tools/cmake" \
  -DCMAKE_PREFIX_PATH="${GITHUB_WORKSPACE}/install/usr" \
  -DCMAKE_VERBOSE_MAKEFILE=ON \
  -DCMAKE_DISABLE_FIND_PACKAGE_RFC=ON \
  -DCOMCAST_CONFIG=OFF \
  -DRDK_SERVICES_COVERITY=ON \
  -DPLUGIN_HDMICECSOURCE=ON \
  -DDS_INCLUDE_DIRS:PATH="${INCPFX}/rdk/ds" \
  -DDSHAL_INCLUDE_DIRS:PATH="${INCPFX}/rdk/halif/ds-hal" \
  -DDSRPC_INCLUDE_DIRS:PATH="${INCPFX}" \
  -DDS_LIBRARIES:FILEPATH="${LIBPFX}/libds.so" \
  -DDSHAL_LIBRARIES:FILEPATH="${LIBPFX}/libdshalcli.so" \
  -DIARMBUS_INCLUDE_DIRS:PATH="${INCPFX}/rdk/iarmbus" \
  -DIARMRECEIVER_INCLUDE_DIRS:PATH="${INCPFX}" \
  -DIARMBUS_LIBRARIES:FILEPATH="${LIBPFX}/libIARMBus.so" \
  -DCEC_INCLUDE_DIRS:PATH="${INCPFX}/ccec/include" \
  -DOSAL_INCLUDE_DIRS:PATH="${INCPFX}/osal/include" \
  -DCEC_LIBRARIES:FILEPATH="${LIBPFX}/libRCEC.so" \
  -DCEC_HAL_LIBRARIES:STRING= \
  -DOSAL_LIBRARIES:FILEPATH="${LIBPFX}/libRCECOSHal.so" \
  -DCMAKE_C_FLAGS="--coverage" \
  -DCMAKE_SHARED_LINKER_FLAGS="--coverage" \
  -DCMAKE_CXX_FLAGS="-DEXCEPTIONS_ENABLE=ON \
  --coverage \
  -Wall -Wno-unused-result -Wno-error=format \
  -DENABLE_TELEMETRY_LOGGING -DUSE_IARMBUS \
  -DUSE_THUNDER_R4 -DTHUNDER_VERSION=4 -DTHUNDER_VERSION_MAJOR=4 -DTHUNDER_VERSION_MINOR=4"

cmake --build build/entservices-hdmicecsource --target install
echo "--- build complete ---"
echo "======================================================================================"
exit 0

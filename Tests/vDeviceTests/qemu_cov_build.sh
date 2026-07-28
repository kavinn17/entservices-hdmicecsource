#!/usr/bin/env bash

set -euo pipefail
set -x

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DEPS_ROOT="${DEPS_ROOT:-${REPO_ROOT}/.deps/vdevice}"
SRC_ROOT="${DEPS_ROOT}/src"
BUILD_ROOT="${BUILD_ROOT:-${REPO_ROOT}/build/vdevice-coverage}"
INSTALL_PREFIX="${INSTALL_PREFIX:-${REPO_ROOT}/install/usr}"
ARTIFACT_DIR="${ARTIFACT_DIR:-${REPO_ROOT}/artifacts/plugins}"

THUNDER_BRANCH="${THUNDER_BRANCH:-R4.4.1}"
THUNDERTOOLS_BRANCH="${THUNDERTOOLS_BRANCH:-${THUNDER_BRANCH}}"
ENTSERVICES_APIS_BRANCH="${ENTSERVICES_APIS_BRANCH:-develop}"
ENTSERVICES_HELPERS_BRANCH="${ENTSERVICES_HELPERS_BRANCH:-develop}"

first_glob_match() {
  local pattern="$1"
  compgen -G "$pattern" | head -n 1 || true
}

detect_vdevice_sysroot() {
  local candidate=""

  candidate="$(first_glob_match "${REPO_ROOT}/../../GCOV/build-vdevice_x86-64-mw/tmp/work/*/entservices-hdmicecsource/*/recipe-sysroot")"
  if [[ -n "${candidate}" ]]; then
    echo "${candidate}"
    return 0
  fi

  candidate="$(first_glob_match "${REPO_ROOT}/../../LATEST_META/build-vdevice_x86-64/tmp/work/*/entservices-hdmicecsource/*/recipe-sysroot")"
  if [[ -n "${candidate}" ]]; then
    echo "${candidate}"
    return 0
  fi

  candidate="$(first_glob_match "${REPO_ROOT}/../../NEW_LED/build-vdevice_x86-64/tmp/work/*/entservices-hdmicecsource/*/recipe-sysroot")"
  if [[ -n "${candidate}" ]]; then
    echo "${candidate}"
    return 0
  fi

  return 1
}

clone_or_update() {
  local repo_dir="$1"
  local repo_url="$2"
  local repo_branch="$3"

  if [[ -d "${repo_dir}/.git" ]]; then
    git -C "${repo_dir}" fetch --depth 1 origin "${repo_branch}"
    git -C "${repo_dir}" checkout -f FETCH_HEAD
    return 0
  fi

  git clone --depth 1 --single-branch --branch "${repo_branch}" "${repo_url}" "${repo_dir}"
}

ensure_packages() {
  if ! command -v apt-get >/dev/null 2>&1; then
    return 0
  fi

  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    ca-certificates \
    cmake \
    curl \
    git \
    libboost-all-dev \
    libcurl4-openssl-dev \
    libdrm-dev \
    libsystemd-dev \
    libunwind-dev \
    ninja-build \
    pkg-config \
    python3-pip
}

ensure_jsonref() {
  if command -v pip3 >/dev/null 2>&1; then
    pip3 install --break-system-packages jsonref || pip3 install jsonref
  fi
}

build_open_dependencies() {
  mkdir -p "${SRC_ROOT}" "${BUILD_ROOT}" "${INSTALL_PREFIX}" "${ARTIFACT_DIR}"

  clone_or_update "${SRC_ROOT}/ThunderTools" "https://github.com/rdkcentral/ThunderTools.git" "${THUNDERTOOLS_BRANCH}"
  clone_or_update "${SRC_ROOT}/Thunder" "https://github.com/rdkcentral/Thunder.git" "${THUNDER_BRANCH}"
  clone_or_update "${SRC_ROOT}/entservices-apis" "https://github.com/rdkcentral/entservices-apis.git" "${ENTSERVICES_APIS_BRANCH}"
  clone_or_update "${SRC_ROOT}/entservices-helpers" "https://github.com/rdkcentral/entservices-helpers.git" "${ENTSERVICES_HELPERS_BRANCH}"

  cmake -G Ninja -S "${SRC_ROOT}/ThunderTools" -B "${BUILD_ROOT}/ThunderTools" \
    -DEXCEPTIONS_ENABLE=ON \
    -DCMAKE_INSTALL_PREFIX="${INSTALL_PREFIX}" \
    -DCMAKE_MODULE_PATH="${INSTALL_PREFIX}/tools/cmake" \
    -DGENERIC_CMAKE_MODULE_PATH="${INSTALL_PREFIX}/tools/cmake"
  cmake --build "${BUILD_ROOT}/ThunderTools" --target install

  cmake -G Ninja -S "${SRC_ROOT}/Thunder" -B "${BUILD_ROOT}/Thunder" \
    -DMESSAGING=ON \
    -DBUILD_TYPE=Debug \
    -DBINDING=127.0.0.1 \
    -DPORT=55555 \
    -DEXCEPTIONS_ENABLE=ON \
    -DCMAKE_INSTALL_PREFIX="${INSTALL_PREFIX}" \
    -DCMAKE_MODULE_PATH="${INSTALL_PREFIX}/tools/cmake" \
    -DGENERIC_CMAKE_MODULE_PATH="${INSTALL_PREFIX}/tools/cmake"
  cmake --build "${BUILD_ROOT}/Thunder" --target install

  rm -f "${SRC_ROOT}/entservices-apis/jsonrpc/DTV.json"
  cmake -G Ninja -S "${SRC_ROOT}/entservices-apis" -B "${BUILD_ROOT}/entservices-apis" \
    -DEXCEPTIONS_ENABLE=ON \
    -DCMAKE_INSTALL_PREFIX="${INSTALL_PREFIX}" \
    -DCMAKE_MODULE_PATH="${INSTALL_PREFIX}/tools/cmake"
  cmake --build "${BUILD_ROOT}/entservices-apis" --target install

  cmake -G Ninja -S "${SRC_ROOT}/entservices-helpers" -B "${BUILD_ROOT}/entservices-helpers" \
    -DEXCEPTIONS_ENABLE=ON \
    -DCMAKE_INSTALL_PREFIX="${INSTALL_PREFIX}" \
    -DCMAKE_MODULE_PATH="${INSTALL_PREFIX}/tools/cmake"
  cmake --build "${BUILD_ROOT}/entservices-helpers" --target install
}

prepare_find_paths() {
  local sysroot="$1"

  export CMAKE_PREFIX_PATH="${INSTALL_PREFIX}:${INSTALL_PREFIX}/lib/cmake"
  export CMAKE_INCLUDE_PATH=""
  export CMAKE_LIBRARY_PATH=""
  export PKG_CONFIG_PATH=""

  if [[ -n "${sysroot}" ]]; then
    export CMAKE_PREFIX_PATH="${CMAKE_PREFIX_PATH}:${sysroot}/usr:${sysroot}/usr/lib/cmake:${sysroot}/usr/share/cmake"
    export CMAKE_FIND_ROOT_PATH="${sysroot}"
    export CMAKE_INCLUDE_PATH="${sysroot}/usr/include:${sysroot}/usr/include/rdk/halif/ds-hal"
    export CMAKE_LIBRARY_PATH="${sysroot}/usr/lib:${sysroot}/lib:${sysroot}/usr/lib64:${sysroot}/lib64"
    export PKG_CONFIG_PATH="${sysroot}/usr/lib/pkgconfig:${sysroot}/usr/share/pkgconfig:${sysroot}/usr/lib64/pkgconfig"
  fi
}

verify_runtime_inputs() {
  local sysroot="$1"

  local missing=0
  local required_paths=(
    "${sysroot}/usr/include/ccec/include/ccec/Connection.hpp"
    "${sysroot}/usr/include/telemetry_busmessage_sender.h"
  )

  local required_lib_patterns=(
    "${sysroot}/usr/lib/libRCEC.so*"
    "${sysroot}/usr/lib/libRCECOSHal.so*"
    "${sysroot}/usr/lib/libIARMBus.so*"
    "${sysroot}/usr/lib/libtelemetry_msgsender.so*"
  )

  local path
  for path in "${required_paths[@]}"; do
    if [[ ! -e "${path}" ]]; then
      echo "Missing required runtime header: ${path}" >&2
      missing=1
    fi
  done

  local pattern
  for pattern in "${required_lib_patterns[@]}"; do
    if [[ -z "$(compgen -G "${pattern}" || true)" ]]; then
      echo "Missing required runtime library matching: ${pattern}" >&2
      missing=1
    fi
  done

  if [[ "${missing}" -ne 0 ]]; then
    echo "Provide a compatible vDevice sysroot using VDEVICE_SYSROOT or place this repo under the LEDCON workspace layout." >&2
    exit 1
  fi
}

build_plugin() {
  local sysroot="$1"
  local plugin_build_dir="${BUILD_ROOT}/entservices-hdmicecsource"

  rm -rf "${plugin_build_dir}"

  cmake -G Ninja -S "${REPO_ROOT}" -B "${plugin_build_dir}" \
    -DUSE_THUNDER_R4=ON \
    -DCOMCAST_CONFIG=OFF \
    -DPLUGIN_HDMICECSOURCE=ON \
    -DRDK_SERVICES_L1_TEST=OFF \
    -DRDK_SERVICE_L2_TEST=OFF \
    -DCMAKE_BUILD_TYPE=Debug \
    -DCMAKE_INSTALL_PREFIX="${INSTALL_PREFIX}" \
    -DCMAKE_MODULE_PATH="${INSTALL_PREFIX}/tools/cmake" \
    -DCMAKE_PREFIX_PATH="${CMAKE_PREFIX_PATH}" \
    -DCMAKE_FIND_ROOT_PATH="${CMAKE_FIND_ROOT_PATH:-}" \
    -DCMAKE_CXX_FLAGS="${CMAKE_CXX_FLAGS:-} --coverage -fprofile-arcs -ftest-coverage" \
    -DCMAKE_C_FLAGS="${CMAKE_C_FLAGS:-} --coverage -fprofile-arcs -ftest-coverage" \
    -DCMAKE_EXE_LINKER_FLAGS="${CMAKE_EXE_LINKER_FLAGS:-} --coverage" \
    -DCMAKE_SHARED_LINKER_FLAGS="${CMAKE_SHARED_LINKER_FLAGS:-} --coverage"

  cmake --build "${plugin_build_dir}" --target install
}

collect_artifacts() {
  mkdir -p "${ARTIFACT_DIR}"
  find "${INSTALL_PREFIX}" -type f -name '*.so' | grep '/plugins/' | tee "${ARTIFACT_DIR}/so-list.txt"
  while IFS= read -r sofile; do
    cp -v "${sofile}" "${ARTIFACT_DIR}/"
  done < "${ARTIFACT_DIR}/so-list.txt"

  test -n "$(ls -A "${ARTIFACT_DIR}"/*.so 2>/dev/null || true)" || {
    echo "No plugin .so files found under ${INSTALL_PREFIX}" >&2
    exit 1
  }
}

main() {
  local sysroot="${VDEVICE_SYSROOT:-}"

  ensure_packages
  ensure_jsonref
  build_open_dependencies

  if [[ -z "${sysroot}" ]]; then
    sysroot="$(detect_vdevice_sysroot || true)"
  fi

  if [[ -z "${sysroot}" ]]; then
    echo "Unable to find a compatible vDevice sysroot automatically." >&2
    echo "Set VDEVICE_SYSROOT to a recipe-sysroot that contains CEC/DS/IARMBus/Telemetry runtime headers and libraries." >&2
    exit 1
  fi

  verify_runtime_inputs "${sysroot}"
  prepare_find_paths "${sysroot}"
  build_plugin "${sysroot}"
  collect_artifacts

  echo "Built plugin artifacts:"
  ls -lh "${ARTIFACT_DIR}"
}

main "$@"
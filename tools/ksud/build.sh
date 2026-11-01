#!/bin/bash
# Rebuild the AERA ARM64 helper from the pinned upstream source and patch.
set -euo pipefail
recipe=$(cd -- "$(dirname -- "$0")" && pwd)
output=$(realpath -m -- "${1:?Pass a new output directory}")
test -n "${ANDROID_NDK_HOME:-}" || { echo 'Set ANDROID_NDK_HOME to NDK r29.' >&2; exit 1; }
mkdir -p -- "$output"
test ! -e "$output/KernelSU" || { echo 'Output source directory already exists.' >&2; exit 1; }
git clone --single-branch --branch v3.3.1 https://github.com/AERA-Recovery/KernelSU.git "$output/KernelSU"
cd -- "$output/KernelSU"
test "$(git rev-parse HEAD)" = 0c0fdb960178fa12d80d6cbcfdcb6ad8be6a865d
test "$(git rev-list --count HEAD)" = 2680
git apply --check "$recipe/ksud-3.3.1-external-modules.patch"
git apply "$recipe/ksud-3.3.1-external-modules.patch"
curl -fL --retry 3 https://github.com/tiann/KernelSU/releases/download/v3.3.1/ksuinit-aarch64 \
    -o userspace/ksud/bin/aarch64/ksuinit
printf '%s  %s\n' 365c66e5435a9ecdb3dbb23ceda2d9253568defeee3682af95220087094eff5d \
    userspace/ksud/bin/aarch64/ksuinit | sha256sum -c -
# Only helper binaries may be present. The source patch also excludes *.ko
# from RustEmbed if modules are accidentally copied into the asset directory.
if find userspace/ksud/bin/aarch64 -name '*.ko' -print -quit | grep -q .; then
    echo 'Unexpected embedded kernel modules in the build inputs.' >&2
    exit 1
fi
export LIBCLANG_PATH="${LIBCLANG_PATH:-$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/lib}"
cargo ndk -t arm64-v8a --platform 26 check --locked --features aera-external-modules -p ksud
cargo ndk -t arm64-v8a --platform 26 clippy --locked --features aera-external-modules -p ksud -- -D warnings
cargo fmt --all
cargo fmt --all -- --check
cargo ndk -t arm64-v8a --platform 26 build --release --locked --features aera-external-modules -p ksud
cargo ndk -t arm64-v8a --platform 26 test --release --locked --features aera-external-modules -p ksud --no-run
cp target/aarch64-linux-android/release/ksud "$output/ksud"
"$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/bin/llvm-strip" --strip-all "$output/ksud"
upx --best --lzma "$output/ksud"
upx -t "$output/ksud"
chmod 0755 "$output/ksud"
sha256sum "$output/ksud"

# AERA ksud 3.3.1 without embedded kernel modules

Upstream: https://github.com/tiann/KernelSU

Base: tag `v3.3.1`, commit `0c0fdb960178fa12d80d6cbcfdcb6ad8be6a865d`.
Original authorship and license remain with KernelSU and its contributors.
The accompanying source patch is the complete AERA modification.

Published source fork (upstream history retained):
https://github.com/AERA-Recovery/KernelSU/tree/aera-ksud-3.3.1

Tested source changes:
https://github.com/AERA-Recovery/KernelSU/commit/8861b9cbda85a37ec20e398a16c6c36489be92fd

Only embedded kernel module bytes are excluded. Commands, Android userspace,
native image patching, module management, resetprop and all helper programs
are retained. The default module lookup reads the separate AERA KernelSU
provider under `/system/etc/aera/root-providers/kernelsu`; explicit
`boot-patch -m MODULE` paths retain precedence for all three providers.
Unsupported names do not become arbitrary filesystem paths.

The eight upstream ARM64 supported-KMI names are preserved separately from
the module assets, so AERA's KMI detection and fallback still work. A name
in that list does not imply the corresponding external module is installed.
Automatic module selection requires the matching external KernelSU module;
other providers still use an explicit module path. No modules are downloaded
or silently substituted by the binary.

Retained assets: upstream ARM64 busybox, bootctl, waitsys and official 3.3.1
ksuinit. The latter is downloaded by the recipe and verified against SHA-256
`365c66e5435a9ecdb3dbb23ceda2d9253568defeee3682af95220087094eff5d`.

## Build

Tested with Rust 1.99.1, cargo-ndk 4.1.2, Android NDK r29, API 26 and UPX 5.1.1.
Install Rust's `aarch64-linux-android` target, rustfmt and Clippy, then run:

```sh
ANDROID_NDK_HOME=/path/to/android-ndk-r29 ./build.sh /path/to/new-output
```

The clone retains upstream history to preserve version code 32680. The
reported version remains `ksud 3.3.1 (uapi: 5)`. The custom build is identified
by this recipe and its recorded hash. The recipe explicitly strips final ELF
symbols using the NDK's llvm-strip, then packs with `upx --best --lzma` and
checks the packed file with `upx -t`.

## Validation

- Android compilation, Clippy with warnings denied, and Rust formatting pass.
- Three ARM64 Android asset/KMI/path-validation unit tests pass under QEMU.
- Version, top-level help and module/boot-patch/boot-info/debug command
  interfaces match the official 3.3.1 binary.
- All four embedded helper programs extract byte-identically to the official
  3.3.1 release.
- All twelve bundled provider/KMI combinations patch a synthetic init_boot
  v4 image; the selected module and ksuinit are verified byte-for-byte and
  the original init is preserved as init.real.
- A missing explicit module fails without producing an output image.
- Default module lookup loads AERA's external KernelSU module correctly.
- All runtime tests use temporary image files. No device is flashed.

`verify.py` accepts a QEMU ARM64 binary and an isolated Android root containing
linker64 and its matching runtime libraries. Place the external provider files
at the matching path within that root. See `--help` for its arguments.
Rooted-Android module lifecycle operations still require device testing; this
rebuild does not change their implementation.

The stripped binary before UPX is 3,957,840 bytes (3.77 MiB):

- Official unstripped 3.3.1: 6,402,736 bytes; 38.2% total saving.
- Official 3.3.1 after the same stripping: 4,990,848 bytes; 20.7% saving.
- AERA's previous stripped 3.3.0: 4,892,712 bytes; 19.1% saving.

These are unpacked ELF sizes, not compressed ramdisk contributions.

Unpacked SHA-256: `b7ffeb7fbef07ba7284a99e392ac318ba50742d030becf26ad1a9788f06d2efc`.

The bundled UPX binary is 2,416,176 bytes (2.30 MiB), SHA-256
`bf3aa594ceeb16d17317888782bd1f2febfcfdea3ccf55011bed3bb928da9dab`.
All twelve image-patch cases, helper extraction, KMI and default external
module lookup checks also pass on the UPX binary under ARM64 emulation.
The packed helper runs on Lighthouse, and Root Manager patching was confirmed
on the device.

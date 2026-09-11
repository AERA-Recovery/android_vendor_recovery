# AERA Recovery Project vendor tree

This repository contains the Android 16 vendor build integration, recovery
utilities, installer assets, and prebuilts used by AERA Recovery Project.

## Release

The first AERA release line is **R1.0**. The canonical release identity is set
in `AERA_A16.sh`; legacy `AERA_*` and `OF_*` variables remain available only
as compatibility interfaces for inherited recovery code and existing device
trees.

## Build

From the Android source root:

```bash
source build/envsetup.sh
lunch twrp_dodge-bp2a-eng
mka adbd recoveryimage
```

Artifacts use the `AERA-R1.0-...` filename prefix.

## Attribution

AERA is built on work from AOSP, TeamWin Recovery Project, OrangeFox Recovery
Project, LineageOS, and their contributors. Preserve existing copyright and
license notices when modifying inherited files.

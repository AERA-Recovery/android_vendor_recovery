# OrangeFox Soong build-var bridge
#
# Soong (the .go *_defaults under bootable/recovery) reads OrangeFox feature
# flags through getMakeVars(), i.e. the "twrpVarsPlugin" SOONG_CONFIG namespace.
# Soong cannot see plain Make variables, so a flag set as "OF_FOO := 1" in a
# device tree .mk only reaches Soong if it is exported into that namespace here.
#
# This list lives in vendor/recovery (OrangeFox-owned) rather than in
# vendor/twrp/config/BoardConfigSoong.mk so that the upstream TWRP config stays
# untouched. It is included from build/make/core/config.mk, right after
# BoardConfigTWRP.mk (which creates the twrpVarsPlugin namespace and runs after
# the device BoardConfig, so the OF_* values are already set by the time we read
# them below).

# Backward compatibility: these flags were historically FOX_*-prefixed because,
# by the old convention, they could only be exported via vendorsetup.sh and not
# declared in a device BoardConfig. They now work from BoardConfig too and have
# moved to the OF_* namespace. Map any legacy FOX_* value onto the new OF_* name
# (with a deprecation warning) before exporting, so old device trees keep
# building.
OF_RENAMED_FROM_FOX := \
    USE_NANO_EDITOR \
    ALLOW_EARLY_SETTINGS_LOAD \
    SETTINGS_ROOT_DIRECTORY \
    MISCELLANEOUS_ROOT_DIRECTORY \
    USE_DATA_RECOVERY_FOR_SETTINGS \
    USE_MEIZU_TOUCH_MAPPING

define fox_renamed_var
ifneq ($$(FOX_$(1)),)
  $$(warning OrangeFox: FOX_$(1) is deprecated; please rename it to OF_$(1))
  OF_$(1) ?= $$(FOX_$(1))
endif
endef

$(foreach v,$(OF_RENAMED_FROM_FOX),$(eval $(call fox_renamed_var,$(v))))

# Bridge the OF_* feature flags into the twrpVarsPlugin Soong namespace so they
# take effect when declared in a device .mk, not only when exported to the
# environment. getMakeVars() in the recovery *_defaults reads these.
$(call add_soong_config_var,twrpVarsPlugin,\
    OF_ENABLE_WLAN \
    OF_ENABLE_LAB \
    OF_SUPPORT_OZIP_DECRYPTION \
    OF_USE_NANO_EDITOR \
    OF_ALLOW_EARLY_SETTINGS_LOAD \
    OF_SETTINGS_ROOT_DIRECTORY \
    OF_MISCELLANEOUS_ROOT_DIRECTORY \
    OF_USE_DATA_RECOVERY_FOR_SETTINGS \
    OF_USE_MEIZU_TOUCH_MAPPING)

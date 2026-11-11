# Standalone original devkitPro/libctru/citro2d sample.
.SUFFIXES:
.DEFAULT_GOAL := all
ifeq ($(strip $(DEVKITARM)),)
$(error DEVKITARM is unset. Install devkitPro and export DEVKITARM)
endif
include $(DEVKITARM)/3ds_rules
TARGET := pocketport-native
BUILD := build
ARCH := -march=armv6k -mtune=mpcore -mfloat-abi=hard -mtp=soft
CFLAGS := -g -O2 -Wall -Wextra -ffunction-sections -fdata-sections $(ARCH) -D__3DS__
LDFLAGS := -specs=3dsx.specs $(ARCH) -Wl,-Map,$(TARGET).map
LIBS := -lcitro2d -lcitro3d -lctru -lm
LIBDIRS := $(CTRULIB) $(DEVKITPRO)/libctru $(DEVKITPRO)/portlibs/3ds
INCLUDE := $(foreach d,$(LIBDIRS),-I$(d)/include)
LIBPATHS := $(foreach d,$(LIBDIRS),-L$(d)/lib)
export _3DSXFLAGS += --romfs=$(CURDIR)/romfs
.PHONY: all clean
all: $(TARGET).3dsx
$(BUILD):
	mkdir -p $@
$(BUILD)/main.o: source/main.c | $(BUILD)
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@
$(TARGET).elf: $(BUILD)/main.o
	$(CC) $(LDFLAGS) $^ $(LIBPATHS) $(LIBS) -o $@
$(TARGET).3dsx: $(TARGET).elf
	3dsxtool $< $@ $(_3DSXFLAGS)
clean:
	rm -rf $(BUILD) $(TARGET).elf $(TARGET).3dsx $(TARGET).map

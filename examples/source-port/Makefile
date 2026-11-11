# Cross-compile the same original C game core and the generated scoring function.
.SUFFIXES:
.DEFAULT_GOAL := all
ifeq ($(strip $(DEVKITARM)),)
$(error DEVKITARM is unset. Install devkitPro and export DEVKITARM)
endif
include $(DEVKITARM)/3ds_rules
TARGET := star-catcher
BUILD := build
ROOT := ../..
ARCH := -march=armv6k -mtune=mpcore -mfloat-abi=hard -mtp=soft
CFLAGS := -g -O2 -Wall -Wextra -ffunction-sections -fdata-sections $(ARCH) -D__3DS__
LDFLAGS := -specs=3dsx.specs $(ARCH) -Wl,-Map,$(TARGET).map
LIBS := -lcitro2d -lcitro3d -lctru -lm
LIBDIRS := $(CTRULIB) $(DEVKITPRO)/libctru $(DEVKITPRO)/portlibs/3ds
INCLUDE := -I$(ROOT)/runtime/core -Igenerated $(foreach d,$(LIBDIRS),-I$(d)/include)
LIBPATHS := $(foreach d,$(LIBDIRS),-L$(d)/lib)
.PHONY: all clean
all: $(TARGET).3dsx
$(BUILD):
	mkdir -p $@
$(BUILD)/main.o: source/main.c | $(BUILD)
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@
$(BUILD)/pp_game.o: $(ROOT)/runtime/core/pp_game.c | $(BUILD)
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@
$(BUILD)/pp_runtime.o: $(ROOT)/runtime/core/pp_runtime.c | $(BUILD)
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@
$(BUILD)/score.o: generated/score.c | $(BUILD)
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@
$(TARGET).elf: $(BUILD)/main.o $(BUILD)/pp_game.o $(BUILD)/pp_runtime.o $(BUILD)/score.o
	$(CC) $(LDFLAGS) $^ $(LIBPATHS) $(LIBS) -o $@
$(TARGET).3dsx: $(TARGET).elf
	3dsxtool $< $@
clean:
	rm -rf $(BUILD) $(TARGET).elf $(TARGET).3dsx $(TARGET).map

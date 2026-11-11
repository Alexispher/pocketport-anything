# Native devkitARM/PICA200 Skyrim static-placement diagnostic frontend.
.SUFFIXES:
.DEFAULT_GOAL := all
ifeq ($(strip $(DEVKITARM)),)
$(error DEVKITARM is unset; install devkitPro devkitARM/libctru/citro3d)
endif
include $(DEVKITARM)/3ds_rules
TARGET := pocketport-skyrim
BUILD := build
ARCH := -march=armv6k -mtune=mpcore -mfloat-abi=hard -mtp=soft
CFLAGS := -std=c99 -O2 -Wall -Wextra -ffunction-sections -fdata-sections $(ARCH) -D__3DS__
LDFLAGS := -specs=3dsx.specs $(ARCH) -Wl,-Map,$(TARGET).map
LIBS := -lcitro3d -lctru -lm
LIBDIRS := $(CTRULIB) $(DEVKITPRO)/portlibs/3ds
INCLUDE := -I../../runtime/skyrim $(foreach d,$(LIBDIRS),-I$(d)/include)
LIBPATHS := $(foreach d,$(LIBDIRS),-L$(d)/lib)
.PHONY: all clean
all: $(TARGET).3dsx
$(BUILD):
	mkdir -p $@
$(BUILD)/vshader.shbin: source/vshader.v.pica | $(BUILD)
	picasso -o $@ $<
$(BUILD)/shader.c: $(BUILD)/vshader.shbin
	python3 ../../scripts/embed_shbin.py $< $@
$(BUILD)/main.o: source/main.c ../../runtime/skyrim/pp_scene.h ../../runtime/skyrim/pp_mesh.h | $(BUILD)
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@
$(BUILD)/pp_scene.o: ../../runtime/skyrim/pp_scene.c ../../runtime/skyrim/pp_scene.h | $(BUILD)
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@
$(BUILD)/pp_mesh.o: ../../runtime/skyrim/pp_mesh.c ../../runtime/skyrim/pp_mesh.h | $(BUILD)
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@
$(BUILD)/shader.o: $(BUILD)/shader.c
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@
$(TARGET).elf: $(BUILD)/main.o $(BUILD)/pp_scene.o $(BUILD)/pp_mesh.o $(BUILD)/shader.o
	$(CC) $(LDFLAGS) $^ $(LIBPATHS) $(LIBS) -o $@
$(TARGET).3dsx: $(TARGET).elf
	3dsxtool $< $@
clean:
	rm -rf $(BUILD) $(TARGET).elf $(TARGET).3dsx $(TARGET).map

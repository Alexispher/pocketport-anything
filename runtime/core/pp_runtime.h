#ifndef POCKETPORT_RUNTIME_HEADER_H
#define POCKETPORT_RUNTIME_HEADER_H

#include <stddef.h>
#include <stdint.h>

/* Portable deterministic utilities; platform-specific graphics/audio are separate. */
typedef struct {
    size_t budget;
    size_t reserved;
    size_t peak;
    unsigned rejects;
} PPMemoryBudget;

void pp_budget_init(PPMemoryBudget *budget, size_t maximum_bytes);
int pp_budget_reserve(PPMemoryBudget *budget, size_t bytes);
void pp_budget_release(PPMemoryBudget *budget, size_t bytes);

/* Hardware-independent input snapshot (not an OS keycode map). */
enum { PP_BUTTON_LEFT = 1u, PP_BUTTON_RIGHT = 2u, PP_BUTTON_ACTION = 4u,
       PP_BUTTON_PAUSE = 8u };
typedef struct { unsigned left, right, action, pause; } PPInputBindings;
unsigned pp_map_input(unsigned raw_buttons, const PPInputBindings *bindings);

/* Reject absolute paths and traversal before resolving a RomFS-relative resource. */
int pp_asset_path_valid(const char *relative);

#endif

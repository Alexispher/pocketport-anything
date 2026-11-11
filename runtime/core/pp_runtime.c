#include "pp_runtime.h"

void pp_budget_init(PPMemoryBudget *b, size_t maximum_bytes) {
    b->budget = maximum_bytes;
    b->reserved = 0;
    b->peak = 0;
    b->rejects = 0;
}

int pp_budget_reserve(PPMemoryBudget *b, size_t bytes) {
    if (bytes > b->budget - b->reserved) {
        ++b->rejects;
        return 0;
    }
    b->reserved += bytes;
    if (b->reserved > b->peak) b->peak = b->reserved;
    return 1;
}

void pp_budget_release(PPMemoryBudget *b, size_t bytes) {
    b->reserved -= bytes > b->reserved ? b->reserved : bytes;
}

unsigned pp_map_input(unsigned raw, const PPInputBindings *b) {
    unsigned out = 0;
    if (raw & b->left) out |= PP_BUTTON_LEFT;
    if (raw & b->right) out |= PP_BUTTON_RIGHT;
    if (raw & b->action) out |= PP_BUTTON_ACTION;
    if (raw & b->pause) out |= PP_BUTTON_PAUSE;
    return out;
}

int pp_asset_path_valid(const char *str) {
    const char *p = str;
    int partlen = 0;
    if (!p || !*p || *p == '/' || *p == '\\') return 0;
    while (*p) {
        char ch = *p;
        if (ch == '\\' || ch == ':' || (unsigned char)ch < 32u) return 0;
        if (ch == '/') {
            if (!partlen) return 0;
            partlen = 0;
        } else {
            if (ch == '.' && (p == str || p[-1] == '/') && p[1] == '.' &&
                (p[2] == '/' || p[2] == '\0')) return 0;
            ++partlen;
        }
        ++p;
    }
    return partlen > 0;
}

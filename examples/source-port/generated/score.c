/* Deterministic translator output; do not hand-edit. */
#include "score.h"
uint32_t pp_score_bonus(uint32_t catches, uint32_t difficulty) {
    uint32_t raw = catches + difficulty;
    uint32_t multiplier = UINT32_C(3);
    uint32_t result = raw * multiplier;
    return result;
}

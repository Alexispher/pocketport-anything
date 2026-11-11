#include "pp_runtime.h"
#include "pp_game.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    PPMemoryBudget mem;
    pp_budget_init(&mem, 128);
    assert(pp_budget_reserve(&mem, 64));
    assert(!pp_budget_reserve(&mem, 70));
    assert(mem.rejects == 1 && mem.peak == 64);
    pp_budget_release(&mem, 32);
    assert(mem.reserved == 32);
    PPInputBindings map = {1u, 2u, 4u, 8u};
    assert(pp_map_input(5u, &map) == (PP_BUTTON_LEFT | PP_BUTTON_ACTION));
    assert(pp_asset_path_valid("levels/chapter1.map"));
    assert(!pp_asset_path_valid("../secret"));
    assert(!pp_asset_path_valid("foo/../bar"));
    assert(!pp_asset_path_valid("/root/file"));
    assert(!pp_asset_path_valid("game\\save"));
    PPGame game;
    pp_game_init(&game, 2026u);
    assert(game.star_x == 6);
    for (unsigned i = 0; i < 66u; ++i)
        pp_game_step(&game, i < 4 ? PP_INPUT_LEFT : 0u);
    assert(game.player_x == 6);
    assert(game.score == 9u && game.missed == 0);
    printf("portable runtime and game core passed; points=%u\n", game.score);
    return 0;
}

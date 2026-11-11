/* Original reusable game core: no platform, heap, filesystem or graphics calls. */
#include "pp_game.h"
#include "score.h" /* PocketPort IR-generated scoring function. */

static uint32_t next_rng(uint32_t *state) {
    uint32_t x = *state;
    x ^= x << 13;
    x ^= x >> 17;
    x ^= x << 5;
    *state = x;
    return x;
}

void pp_game_init(PPGame *game, uint32_t seed) {
    game->player_x = PP_GAME_W / 2;
    game->star_x = (int)(seed % PP_GAME_W);
    game->star_y = 0;
    game->score = 0;
    game->rng = seed ? seed : 1u;
    game->missed = 0;
    game->ticks = 0;
    game->game_over = 0;
}

void pp_game_step(PPGame *game, unsigned input) {
    if (input & PP_INPUT_RESTART) {
        pp_game_init(game, game->rng);
        return;
    }
    if (game->game_over) return;
    if ((input & PP_INPUT_LEFT) && game->player_x > 0) --game->player_x;
    if ((input & PP_INPUT_RIGHT) && game->player_x + 1 < PP_GAME_W) ++game->player_x;
    ++game->ticks;
    /* The original portable source game updates once every 6 render frames. */
    if (game->ticks % 6u != 0u) return;
    ++game->star_y;
    if (game->star_y >= PP_GAME_H - 1) {
        if (game->player_x == game->star_x) {
            game->score += pp_score_bonus(1u, 2u);
        } else {
            ++game->missed;
            if (game->missed >= 3u) game->game_over = 1;
        }
        game->star_y = 0;
        game->star_x = (int)(next_rng(&game->rng) % PP_GAME_W);
    }
}

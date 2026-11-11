#ifndef POCKETPORT_GAME_HEADER_H
#define POCKETPORT_GAME_HEADER_H
#include <stdint.h>

enum { PP_GAME_W = 20, PP_GAME_H = 12 };
enum { PP_INPUT_LEFT = 1u, PP_INPUT_RIGHT = 2u, PP_INPUT_RESTART = 4u };

typedef struct {
    int player_x;
    int star_x;
    int star_y;
    uint32_t score;
    uint32_t rng;
    unsigned missed;
    unsigned ticks;
    int game_over;
} PPGame;

void pp_game_init(PPGame *game, uint32_t seed);
void pp_game_step(PPGame *game, unsigned input);

#endif

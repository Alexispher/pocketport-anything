/* Portable host interface for the same actual game core compiled for 3DS. */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "pp_game.h"
#include "pp_runtime.h"

int main(int argc, char **argv) {
    PPGame game;
    const char *script = "RRRRLLLLNNNNNNNNNNNNNNNNNN";
    unsigned i;
    if (argc == 3 && strcmp(argv[1], "--script") == 0) script = argv[2];
    else if (argc != 1) {
        fputs("usage: star-catcher-host [--script LRNB...]\n", stderr);
        return 2;
    }
    PPInputBindings bindings = {1u, 2u, 4u, 8u};
    pp_game_init(&game, 2026u);
    for (i = 0; script[i]; ++i) {
        unsigned input = 0;
        if (script[i] == 'L') input = PP_INPUT_LEFT;
        else if (script[i] == 'R') input = PP_INPUT_RIGHT;
        else if (script[i] == 'B') input = PP_INPUT_RESTART;
        else if (script[i] != 'N') {
            fprintf(stderr, "Invalid script character: %c\n", script[i]);
            return 2;
        }
        pp_game_step(&game, pp_map_input(input, &bindings));
    }
    printf("ticks=%u player=%d star=%d,%d score=%u missed=%u over=%d\n",
           game.ticks, game.player_x, game.star_x, game.star_y,
           game.score, game.missed, game.game_over);
    return 0;
}

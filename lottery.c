#include <allegro5/allegro_primitives.h>
#include <allegro5/allegro_font.h>
#include <allegro5/allegro_ttf.h> 
#include "globals.h"
#include "lottery.h"
#include "types.h"

void init_lottery(void) {
}

void render_lottery(void) {
    al_clear_to_color(al_map_rgb(50, 50, 70)); // Dark blue-grey background
}

void handle_lottery_input(ALLEGRO_EVENT ev) {
    if (ev.type == ALLEGRO_EVENT_KEY_DOWN) {
        if (ev.keyboard.keycode == ALLEGRO_KEY_ESCAPE) {
            game_phase = GROWTH;
        }
    }
}

void update_lottery(void) {
}

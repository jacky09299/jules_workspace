#include <allegro5/allegro_primitives.h>
#include <allegro5/allegro_font.h>
#include <allegro5/allegro_ttf.h> 
#include "globals.h"
#include "minigame2.h"
#include "types.h"

void init_minigame2(void) {
}

void render_minigame2(void) {
    al_clear_to_color(al_map_rgb(50, 50, 70)); // Dark blue-grey background
}

void handle_minigame2_input(ALLEGRO_EVENT ev) {
    if (ev.type == ALLEGRO_EVENT_KEY_DOWN) {
        if (ev.keyboard.keycode == ALLEGRO_KEY_ESCAPE) {
            game_phase = GROWTH;
        }
    }
}

void update_minigame2(void) {
}

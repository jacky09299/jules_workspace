#ifndef GRAPHICS_H
#define GRAPHICS_H

#include <allegro5/allegro.h> // For ALLEGRO_BITMAP

// Asset loading could also go here, or in a separate assets.h/c
void load_game_assets(void);
void destroy_game_assets(void);

ALLEGRO_BITMAP* create_background_tile_texture(int tile_size, int num_tiles_w, int num_tiles_h);
void render_battle_scene(void);
void render_player_knife(void); // Part of battle scene rendering

#endif // GRAPHICS_H
#ifndef GAME_STATE_H
#define GAME_STATE_H
#include <allegro5/allegro.h>
#include "types.h" // For GamePhase, Button

void init_menu_buttons(void);
void init_growth_buttons(void);

void render_main_menu(void);
void render_growth_screen(void);

void handle_main_menu_input(ALLEGRO_EVENT ev);
void handle_growth_screen_input(ALLEGRO_EVENT ev);
void handle_battle_scene_input_actions(ALLEGRO_EVENT ev); // Could also be in input.h/c

// Growth button actions
void on_minigame1_button_click(void);
void on_minigame2_button_click(void);
void on_lottery_button_click(void);
void on_backpack_button_click(void);

#endif // GAME_STATE_H
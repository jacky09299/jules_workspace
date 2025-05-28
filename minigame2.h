#ifndef MINIGAME2_H
#define MINIGAME2_H

#include <allegro5/allegro.h>
#include "types.h" // For Button, GamePhase, ALLEGRO_EVENT

// 初始化、畫面渲染、輸入處理、更新函式宣告
void init_minigame2(void);
void render_minigame2(void);
void handle_minigame2_input(ALLEGRO_EVENT ev);
void update_minigame2(void);

#endif // MINIGAME2_H

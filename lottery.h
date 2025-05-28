#ifndef LOTTERY_H
#define LOTTERY_H

#include <allegro5/allegro.h>
#include "types.h" // For Button, GamePhase, ALLEGRO_EVENT

// 初始化、畫面渲染、輸入處理、更新函式宣告
void init_lottery(void);
void render_lottery(void);
void handle_lottery_input(ALLEGRO_EVENT ev);
void update_lottery(void);

#endif // LOTTERY_H

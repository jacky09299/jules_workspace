#include "escape_gate.h"
#include "globals.h"
#include "player.h"
#include "config.h"
#include <allegro5/allegro_primitives.h>

/**
 * 初始化逃生門的狀態。
 */
void init_escape_gate() {
    escape_gate.x = -200;
    escape_gate.y = 150;
    escape_gate.width = 80;
    escape_gate.height = 100;
    escape_gate.is_active = true;
    escape_gate.is_counting_down = false;
    escape_gate.countdown_frames = 300; // 3秒倒數 (假設60FPS)
}

/**
 * 更新逃生門的邏輯，包括偵測玩家碰撞與倒數邏輯。
 */
void update_escape_gate() {
    if (!escape_gate.is_active) return;

    float px = player.x;
    float py = player.y;

    bool player_in_gate =
        (px >= escape_gate.x && px <= escape_gate.x + escape_gate.width &&
         py >= escape_gate.y && py <= escape_gate.y + escape_gate.height);

    if (player_in_gate) {
        if (!escape_gate.is_counting_down) {
            escape_gate.is_counting_down = true;
            escape_gate.countdown_frames = 300;
        } else {
            escape_gate.countdown_frames--;
            if (escape_gate.countdown_frames <= 0) {
                // 逃離成功，切換回養成畫面
                escape_gate.is_active = false;
                escape_gate.is_counting_down = false;
                escape_gate.countdown_frames = 0;

                game_phase = GROWTH;
                day_time = 1;
                current_day++;

                camera_x = player.x - SCREEN_WIDTH / 2;
                camera_y = player.y - SCREEN_HEIGHT / 2;
            }
        }
    } else {
        // 玩家離開門範圍，中止倒數
        escape_gate.is_counting_down = false;
    }
}

/**
 * 繪製逃生門與倒數提示。
 */
void render_escape_gate(ALLEGRO_FONT* font) {
    if (!escape_gate.is_active) return;

    float screen_x = escape_gate.x - camera_x;
    float screen_y = escape_gate.y - camera_y;

    al_draw_filled_rectangle(
        screen_x, screen_y,
        screen_x + escape_gate.width,
        screen_y + escape_gate.height,
        al_map_rgb(150, 150, 255)
    );

    if (escape_gate.is_counting_down) {
        int bar_width = 60;
        int bar_height = 10;
        int max_frames = 300;
        float ratio = (float)escape_gate.countdown_frames / max_frames;
        float filled_width = ratio * bar_width;

        int seconds_left = escape_gate.countdown_frames / 60;
        al_draw_textf(font, al_map_rgb(255, 0, 0),
            screen_x + escape_gate.width / 2,
            screen_y - 20,
            ALLEGRO_ALIGN_CENTER,
            "逃離中：%d", seconds_left);

         // 外框
        al_draw_rectangle(
            screen_x + 10,
            screen_y - 30,
            screen_x + 10 + bar_width,
            screen_y - 30 + bar_height,
            al_map_rgb(255, 255, 255),
            1.5f
        );

        // 內填充
        al_draw_filled_rectangle(
            screen_x + 10,
            screen_y - 30,
            screen_x + 10 + filled_width,
            screen_y - 30 + bar_height,
            al_map_rgb(255, 255, 0)
        );
    }
}

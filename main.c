#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <math.h>
#include <time.h>

#include <allegro5/allegro.h>
#include <allegro5/allegro_font.h>
#include <allegro5/allegro_ttf.h>
#include <allegro5/allegro_primitives.h>
#include <allegro5/allegro_image.h>

#include "config.h"
#include "types.h"
#include "globals.h"
#include "player.h"
#include "boss.h"
#include "projectile.h"
#include "game_state.h"
#include "graphics.h"
#include "escape_gate.h"
#include "minigame1.h"
#include "minigame2.h"
#include "lottery.h"
#include "backpack.h"
/**
 * 初始化遊戲所需的 Allegro 系統、資源和遊戲物件。
 */
void init_game_systems_and_assets() {
    al_init(); 
    srand(time(NULL)); 

    al_init_font_addon();      
    al_init_ttf_addon();       
    al_init_primitives_addon();
    al_init_image_addon();     
    al_install_keyboard();     
    al_install_mouse();        

    display = al_create_display(SCREEN_WIDTH, SCREEN_HEIGHT);
    al_set_window_title(display, "遊戲"); 

    font = al_load_ttf_font("assets/font/JasonHandwriting3.ttf", 20, 0); 

    event_queue = al_create_event_queue();
    timer = al_create_timer(1.0 / FPS); 

    al_register_event_source(event_queue, al_get_display_event_source(display));    
    al_register_event_source(event_queue, al_get_keyboard_event_source());   
    al_register_event_source(event_queue, al_get_mouse_event_source());      
    al_register_event_source(event_queue, al_get_timer_event_source(timer));     

    for (int i = 0; i < ALLEGRO_KEY_MAX; i++) keys[i] = false;

    load_game_assets(); //載入圖片
    
    init_player();                
    init_player_knife();
    init_bosses_by_archetype();            
    init_projectiles();                    
    init_menu_buttons();                   
    init_growth_buttons();
    init_escape_gate();
    game_phase = MENU;                     

    al_start_timer(timer); 
}

/**
 * 關閉遊戲系統並釋放已分配的資源。
 */
void shutdown_game_systems_and_assets() {
    destroy_game_assets(); 

    al_destroy_font(font);
    al_destroy_timer(timer);
    al_destroy_event_queue(event_queue);
    al_destroy_display(display);

    al_shutdown_font_addon();
    al_shutdown_ttf_addon();
    al_shutdown_primitives_addon();
    al_shutdown_image_addon();
}


/**
 * 遊戲主函數。
 */
int main() {
    init_game_systems_and_assets(); 
    bool game_is_running = true;    
    bool needs_redraw = true;       

    while (game_is_running && game_phase != EXIT) {
        ALLEGRO_EVENT ev;
        al_wait_for_event(event_queue, &ev); 

        if (ev.type == ALLEGRO_EVENT_KEY_DOWN) { //按鍵列表中被按下的按鍵設為true
            keys[ev.keyboard.keycode] = true;
        } else if (ev.type == ALLEGRO_EVENT_KEY_UP) { //按鍵列表中被按下的按鍵設為false
            keys[ev.keyboard.keycode] = false;
        }

        //每 1/FPS 秒執行一次
        if (ev.timer.source == timer) { 
            needs_redraw = true; 
            if (game_phase == BATTLE) { 
                player.v_x = 0; player.v_y = 0; 
                if (keys[ALLEGRO_KEY_W] || keys[ALLEGRO_KEY_UP]) player.v_y -= 1.0f;    
                if (keys[ALLEGRO_KEY_S] || keys[ALLEGRO_KEY_DOWN]) player.v_y += 1.0f;  
                if (keys[ALLEGRO_KEY_A] || keys[ALLEGRO_KEY_LEFT]) player.v_x -= 1.0f;  
                if (keys[ALLEGRO_KEY_D] || keys[ALLEGRO_KEY_RIGHT]) player.v_x += 1.0f; 

                if (player.v_x != 0 || player.v_y != 0) {
                    float magnitude = sqrtf(player.v_x * player.v_x + player.v_y * player.v_y); 
                    player.v_x = (player.v_x / magnitude) * player.speed; 
                    player.v_y = (player.v_y / magnitude) * player.speed;
                }
                
                if (player.normal_attack_cooldown_timer > 0) {
                    player.normal_attack_cooldown_timer--;
                }

                // 更新玩家、boss、攻擊、視角
                update_player_character(); 
                update_player_knife();
                for (int i = 0; i < MAX_BOSSES; ++i) { 
                    update_boss_character(&bosses[i]); 
                }
                update_active_projectiles(); 
                update_game_camera();
                update_escape_gate();
                        

                if (player.hp <= 0) { 
                    printf("遊戲結束 - 你被擊敗了！\n");
                    game_phase = MENU; 
                    for (int i = 0; i < 3; ++i) { menu_buttons[i].is_hovered = false; }
                }
                bool all_bosses_defeated_this_round = true; 
                for (int i = 0; i < MAX_BOSSES; ++i) {
                    if (bosses[i].is_alive) { 
                        all_bosses_defeated_this_round = false; 
                        break; 
                    }
                }
                if (all_bosses_defeated_this_round && MAX_BOSSES > 0) { // 戰鬥階段勝利判斷
                    int money_earned = 500 * MAX_BOSSES; 
                    player.money += money_earned; 

                    // 進入下一天
                    current_day++;
                    day_time = 1;
                    game_phase = GROWTH;

                    // 關閉 escape gate 狀態（以免殘留）
                    escape_gate.is_active = false;
                    escape_gate.is_counting_down = false;
                    escape_gate.countdown_frames = 0;

                    // 重設 UI 狀態
                    for (int i = 0; i < 3; ++i) {
                        menu_buttons[i].is_hovered = false;
                    }
                    for (int i = 0; i < MAX_GROWTH_BUTTONS; ++i) {
                        growth_buttons[i].is_hovered = false;
                    }
                    // 顯示訊息（可畫在畫面上，或加 audio）
                    snprintf(growth_message, sizeof(growth_message), "勝利！獲得了 %d 金幣", money_earned);
                    growth_message_timer = 180; // 顯示 3 秒
                }
            }
            if (game_phase == MINIGAME1) {
                update_minigame1();
            }
            if (game_phase == MINIGAME2) {
                update_minigame2();
            }
            if (game_phase == LOTTERY) {
                update_lottery();
            }
            if (game_phase == BACKPACK) {
                update_backpack();
            }
        } 
        else if (ev.type == ALLEGRO_EVENT_DISPLAY_CLOSE) { //按視窗叉叉，關閉遊戲
            game_is_running = false; 
        } 
        else if (ev.type == ALLEGRO_EVENT_MOUSE_AXES) { //偵測到滑鼠移動時執行
             if (game_phase == BATTLE) { //更新玩家面向角度
                float player_screen_center_x = SCREEN_WIDTH / 2.0f;
                float player_screen_center_y = SCREEN_HEIGHT / 2.0f;
                player.facing_angle = atan2(ev.mouse.y - player_screen_center_y, ev.mouse.x - player_screen_center_x); 
            } else if (game_phase == MENU) { 
                 handle_main_menu_input(ev);
            } else if (game_phase == GROWTH) {
                 handle_growth_screen_input(ev);
            } else if (game_phase == MINIGAME1) {
                 handle_minigame1_input(ev);
            } else if (game_phase == MINIGAME2) {
                 handle_minigame2_input(ev);
            } else if (game_phase == LOTTERY) {
                 handle_lottery_input(ev);
            } else if (game_phase == BACKPACK) {
                 handle_backpack_input(ev);
            }
        }
        else { 
            switch (game_phase) {
                case MENU: handle_main_menu_input(ev); break;
                case GROWTH: handle_growth_screen_input(ev); break;
                case BATTLE: handle_battle_scene_input_actions(ev); break;
                case MINIGAME1: handle_minigame1_input(ev); break;
                case MINIGAME2: handle_minigame2_input(ev); break;
                case LOTTERY: handle_lottery_input(ev); break;
                case BACKPACK: handle_backpack_input(ev); break;
                default: break;
            }
        }

        if (needs_redraw && al_is_event_queue_empty(event_queue)) {
            needs_redraw = false; 
            switch (game_phase) {
                case MENU: render_main_menu(); break;
                case GROWTH: render_growth_screen(); break;
                case BATTLE: 
                    render_battle_scene(); 
                    render_escape_gate(font); 
                    break;
                case MINIGAME1: render_minigame1(); break;
                case MINIGAME2: render_minigame2(); break;
                case LOTTERY: render_lottery(); break;
                case BACKPACK: render_backpack(); break;
                default: break;
            }
            al_flip_display(); 
        }
    }

    shutdown_game_systems_and_assets(); 
    return 0;
}
#include "graphics.h"
#include "globals.h"    // For all game objects, camera, assets, font
#include "config.h"     // For screen/sprite dimensions, FPS
#include "utils.h"   
#include <allegro5/allegro_primitives.h> // For drawing shapes
#include <allegro5/allegro_image.h>
#include <stdio.h>      // For printf, sprintf
#include <math.h>       // For floor, cos, sin

/**
 * 載入遊戲圖像資源。
 */
void load_game_assets(void) {
    player_sprite_asset = al_load_bitmap("assets/image/player.png");
    
    boss_archetype_tank_sprite_asset = al_load_bitmap("assets/image/boss1.png");
    
    boss_archetype_skillful_sprite_asset = al_load_bitmap("assets/image/boss2.png");
    
    boss_archetype_berserker_sprite_asset = al_load_bitmap("assets/image/boss3.png");
    
    knife_sprite_asset = al_load_bitmap("assets/image/knife.png");

    background_texture = create_background_tile_texture(100, 2, 2); 
}

/**
 * 釋放遊戲圖像資源。
 */
void destroy_game_assets(void) {
    if (player_sprite_asset) al_destroy_bitmap(player_sprite_asset);
    if (boss_archetype_tank_sprite_asset) al_destroy_bitmap(boss_archetype_tank_sprite_asset);
    if (boss_archetype_skillful_sprite_asset) al_destroy_bitmap(boss_archetype_skillful_sprite_asset);
    if (boss_archetype_berserker_sprite_asset) al_destroy_bitmap(boss_archetype_berserker_sprite_asset);
    if (knife_sprite_asset) al_destroy_bitmap(knife_sprite_asset);
    if (background_texture) al_destroy_bitmap(background_texture);
}


/**
 * 創建一個可重複平鋪的背景紋理。
 */
ALLEGRO_BITMAP* create_background_tile_texture(int tile_size, int num_tiles_w, int num_tiles_h) {
    ALLEGRO_BITMAP* bg = al_create_bitmap(tile_size * num_tiles_w, tile_size * num_tiles_h);
    if (!bg) {
        fprintf(stderr, "創建背景紋理失敗！\n");
        return NULL;
    }
    ALLEGRO_STATE old_state;
    al_store_state(&old_state, ALLEGRO_STATE_TARGET_BITMAP); 
    al_set_target_bitmap(bg); 

    for (int r = 0; r < num_tiles_h; ++r) {
        for (int c = 0; c < num_tiles_w; ++c) {
            ALLEGRO_COLOR color = ((r + c) % 2 == 0) ? al_map_rgb(40, 60, 40) : al_map_rgb(50, 70, 50); 
            al_draw_filled_rectangle(c * tile_size, r * tile_size, (c + 1) * tile_size, (r + 1) * tile_size, color);
        }
    }
    // Example accent, remove if not desired
    al_draw_filled_circle(tile_size * num_tiles_w * 0.25f, tile_size * num_tiles_h * 0.25f, 10, al_map_rgb(100,20,20));
    al_restore_state(&old_state); 
    return bg;
}

/**
 * 渲染戰鬥場景。
 */
void render_battle_scene() {
    al_clear_to_color(al_map_rgb(10, 10, 10)); 

    if (background_texture) {
        float tex_w = al_get_bitmap_width(background_texture);   
        float tex_h = al_get_bitmap_height(background_texture);  
        if (tex_w > 0 && tex_h > 0) { 
            float cam_vx1 = camera_x, cam_vy1 = camera_y; 
            float cam_vx2 = camera_x + SCREEN_WIDTH, cam_vy2 = camera_y + SCREEN_HEIGHT; 
            int tile_start_x = floor(cam_vx1/tex_w); 
            int tile_start_y = floor(cam_vy1/tex_h); 
            int tile_end_x = floor((cam_vx2-1)/tex_w); 
            int tile_end_y = floor((cam_vy2-1)/tex_h); 
            for (int ty = tile_start_y; ty <= tile_end_y; ++ty) {
                for (int tx = tile_start_x; tx <= tile_end_x; ++tx) {
                    al_draw_bitmap(background_texture, (tx*tex_w)-camera_x, (ty*tex_h)-camera_y, 0); 
                }
            }
        }
    }

    for (int i = 0; i < MAX_BOSSES; ++i) {
        if (bosses[i].is_alive) { 
            float boss_screen_x = bosses[i].x - camera_x; 
            float boss_screen_y = bosses[i].y - camera_y; 
            ALLEGRO_BITMAP* current_boss_sprite_asset = bosses[i].sprite_asset; 

            if (current_boss_sprite_asset) { 
                float src_w = al_get_bitmap_width(current_boss_sprite_asset);    
                float src_h = al_get_bitmap_height(current_boss_sprite_asset);   
                if (src_w == 0 || src_h == 0) { 
                     al_draw_filled_circle(boss_screen_x, boss_screen_y, bosses[i].collision_radius, al_map_rgb(255,0,255)); 
                } else {
                    float scale_x = bosses[i].target_display_width / src_w;
                    float scale_y = bosses[i].target_display_height / src_h;
                    al_draw_scaled_rotated_bitmap(current_boss_sprite_asset,
                                                src_w / 2.0f, src_h / 2.0f,  
                                                boss_screen_x, boss_screen_y, 
                                                scale_x, scale_y,           
                                                bosses[i].facing_angle,     
                                                0);                         
                }                     
            } else { 
                ALLEGRO_COLOR boss_fallback_color; 
                switch(bosses[i].archetype){
                    case BOSS_TYPE_TANK: boss_fallback_color = al_map_rgb(100,100,220); break; 
                    case BOSS_TYPE_SKILLFUL: boss_fallback_color = al_map_rgb(220,100,220); break; 
                    case BOSS_TYPE_BERSERKER: boss_fallback_color = al_map_rgb(220,60,60); break; 
                    default: boss_fallback_color = al_map_rgb(180,180,180); break; 
                }
                al_draw_filled_circle(boss_screen_x, boss_screen_y, bosses[i].collision_radius, boss_fallback_color); 
            }
            float text_y_offset = bosses[i].target_display_height / 2.0f + 7; 
            const char* archetype_str_label = ""; 
            switch(bosses[i].archetype){
                case BOSS_TYPE_TANK: archetype_str_label = "坦克"; break;
                case BOSS_TYPE_SKILLFUL: archetype_str_label = "法師"; break; 
                case BOSS_TYPE_BERSERKER: archetype_str_label = "猛獸"; break; 
            }
            al_draw_textf(font, al_map_rgb(255,255,255), boss_screen_x, boss_screen_y - text_y_offset - 40, ALLEGRO_ALIGN_CENTER, "ID:%d %s", bosses[i].id, archetype_str_label);
            al_draw_textf(font, al_map_rgb(255,255,255), boss_screen_x, boss_screen_y - text_y_offset - 20, ALLEGRO_ALIGN_CENTER, "HP: %d/%d", bosses[i].hp, bosses[i].max_hp);
            al_draw_textf(font, al_map_rgb(200,200,200), boss_screen_x, boss_screen_y - text_y_offset, ALLEGRO_ALIGN_CENTER, "力:%d 防:%d 魔:%d 速:%.1f", bosses[i].strength, bosses[i].defense, bosses[i].magic, bosses[i].speed);
        }
    }

    float player_screen_x = SCREEN_WIDTH/2.0f;  
    float player_screen_y = SCREEN_HEIGHT/2.0f; 
    if (player_sprite_asset) { 
        float src_w = al_get_bitmap_width(player_sprite_asset);
        float src_h = al_get_bitmap_height(player_sprite_asset);
        if(src_w > 0 && src_h > 0){ 
            float scale_x = (float)PLAYER_TARGET_WIDTH / src_w;  
            float scale_y = (float)PLAYER_TARGET_HEIGHT / src_h; 
            al_draw_scaled_rotated_bitmap(player_sprite_asset,
                                        src_w / 2.0f, src_h / 2.0f, 
                                        player_screen_x, player_screen_y,      
                                        scale_x, scale_y,          
                                        player.facing_angle,       
                                        0);       
        } else { 
             al_draw_filled_circle(player_screen_x, player_screen_y, PLAYER_SPRITE_SIZE, al_map_rgb(0,100,200)); 
        }                 
    } else { 
        al_draw_filled_circle(player_screen_x, player_screen_y, PLAYER_SPRITE_SIZE, al_map_rgb(0,100,200)); 
        float line_end_x = player_screen_x + cos(player.facing_angle) * PLAYER_SPRITE_SIZE * 1.5f;
        float line_end_y = player_screen_y + sin(player.facing_angle) * PLAYER_SPRITE_SIZE * 1.5f;
        al_draw_line(player_screen_x, player_screen_y, line_end_x, line_end_y, al_map_rgb(255,255,255), 2.0f);
    }
    render_player_knife();

    float player_text_y_offset = (player_sprite_asset ? PLAYER_TARGET_HEIGHT / 2.0f : PLAYER_SPRITE_SIZE) + 5; 
    al_draw_textf(font, al_map_rgb(255,255,255), player_screen_x, player_screen_y - player_text_y_offset - 20, ALLEGRO_ALIGN_CENTER,"玩家 (力:%d 魔:%d)", player.strength, player.magic);
    al_draw_textf(font, al_map_rgb(180,255,180), player_screen_x, player_screen_y - player_text_y_offset, ALLEGRO_ALIGN_CENTER,"HP: %d/%d", player.hp, player.max_hp);

    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (projectiles[i].active) { 
            float proj_screen_x = projectiles[i].x - camera_x; 
            float proj_screen_y = projectiles[i].y - camera_y; 
            ALLEGRO_COLOR proj_color; 
            switch(projectiles[i].type) {
                case PROJ_TYPE_WATER: proj_color = al_map_rgb(0, 150, 255); break;   
                case PROJ_TYPE_FIRE: proj_color = al_map_rgb(255, 100, 0); break;  
                case PROJ_TYPE_ICE: proj_color = al_map_rgb(150, 255, 255); break;  
                case PROJ_TYPE_PLAYER_FIREBALL: proj_color = al_map_rgb(255, 50, 50); break; 
                case PROJ_TYPE_GENERIC: 
                default: proj_color = al_map_rgb(200, 200, 200); break; 
            }
            al_draw_filled_circle(proj_screen_x, proj_screen_y, PROJECTILE_RADIUS, proj_color); 
            if (projectiles[i].type == PROJ_TYPE_ICE) {
                al_draw_circle(proj_screen_x, proj_screen_y, PROJECTILE_RADIUS + 2, al_map_rgb(255, 255, 255), 1.0f); 
            } else if (projectiles[i].type == PROJ_TYPE_PLAYER_FIREBALL || projectiles[i].type == PROJ_TYPE_FIRE) {
                al_draw_circle(proj_screen_x, proj_screen_y, PROJECTILE_RADIUS + 1, al_map_rgb(255, 200, 0), 1.0f); 
            }
        }
    }

    if (player.skill_cooldown_timers[SKILL_LIGHTNING_BOLT] == PLAYER_LIGHTNING_SKILL_COOLDOWN - 1) { // Render for one frame after use
        for (int i = 0; i < MAX_BOSSES; ++i) {
            if (bosses[i].is_alive) { 
                float dist = calculate_distance_between_points(player.x, player.y, bosses[i].x, bosses[i].y); 
                if (dist < PLAYER_LIGHTNING_RANGE) { 
                    float boss_screen_x = bosses[i].x - camera_x;
                    float boss_screen_y = bosses[i].y - camera_y;
                    al_draw_line(player_screen_x, player_screen_y, boss_screen_x, boss_screen_y, al_map_rgb(255, 255, 0), 3.0f);
                }
            }
        }
    }

    al_draw_textf(font, al_map_rgb(220,220,220), 10, 10, 0, "玩家世界座標: (%.0f, %.0f)", player.x, player.y);
    
    int ui_skill_text_y_start = SCREEN_HEIGHT - 140; 
    const char* skill_key_hints[] = {"", "K", "L", "U", "I", "O"}; 
    const char* skill_display_names[] = {"", "水彈", "冰錐", "閃電", "治療", "火球"}; 
    for (PlayerSkillIdentifier skill_id_enum_val = SKILL_WATER_ATTACK; skill_id_enum_val <= SKILL_FIREBALL; ++skill_id_enum_val) {
        if (player.learned_skills[skill_id_enum_val] != SKILL_NONE) { 
            char skill_status_text[60]; 
            if (player.skill_cooldown_timers[skill_id_enum_val] > 0) { 
                sprintf(skill_status_text, "%s(%s): 冷卻 %ds", skill_display_names[skill_id_enum_val], skill_key_hints[skill_id_enum_val],
                       player.skill_cooldown_timers[skill_id_enum_val]/FPS + 1); 
            } else { 
                sprintf(skill_status_text, "%s(%s): 就緒", skill_display_names[skill_id_enum_val], skill_key_hints[skill_id_enum_val]);
            }
            ALLEGRO_COLOR text_color = (player.skill_cooldown_timers[skill_id_enum_val] > 0)
                                 ? al_map_rgb(150, 150, 150) 
                                 : al_map_rgb(150, 255, 150); 
            al_draw_text(font, text_color, 10, ui_skill_text_y_start + (skill_id_enum_val-1) * 20, 0, skill_status_text);
        }
    }
    al_draw_text(font, al_map_rgb(200,200,200), SCREEN_WIDTH - 10, 10, ALLEGRO_ALIGN_RIGHT, "操作說明:");
    al_draw_text(font, al_map_rgb(180,180,180), SCREEN_WIDTH - 10, 35, ALLEGRO_ALIGN_RIGHT, "J: 攻擊");
    al_draw_text(font, al_map_rgb(180,180,180), SCREEN_WIDTH - 10, 55, ALLEGRO_ALIGN_RIGHT, "K: 水彈 | L: 冰錐");
    al_draw_text(font, al_map_rgb(180,180,180), SCREEN_WIDTH - 10, 75, ALLEGRO_ALIGN_RIGHT, "U: 閃電 | I: 治療");
    al_draw_text(font, al_map_rgb(180,180,180), SCREEN_WIDTH - 10, 95, ALLEGRO_ALIGN_RIGHT, "O: 火球 | ESC: 選單");
}


/**
 * 渲染玩家的刀子攻擊動畫。
 */
void render_player_knife() {
    if (!player_knife.active || !knife_sprite_asset) {
        return;
    }

    float knife_screen_x = player_knife.x - camera_x;
    float knife_screen_y = player_knife.y - camera_y;

    float src_w = al_get_bitmap_width(knife_sprite_asset);
    float src_h = al_get_bitmap_height(knife_sprite_asset);

    if (src_w > 0 && src_h > 0) {
        float scale_x = (float)KNIFE_SPRITE_WIDTH / src_w;
        float scale_y = (float)KNIFE_SPRITE_HEIGHT / src_h;

        al_draw_scaled_rotated_bitmap(knife_sprite_asset,
                                      src_w / 2.0f, src_h / 2.0f, 
                                      knife_screen_x, knife_screen_y, 
                                      scale_x, scale_y,             
                                      player_knife.angle,           
                                      0);
    } else { 
        al_draw_filled_rectangle(knife_screen_x - KNIFE_SPRITE_WIDTH/4, knife_screen_y - KNIFE_SPRITE_HEIGHT/4, 
                                 knife_screen_x + KNIFE_SPRITE_WIDTH/4, knife_screen_y + KNIFE_SPRITE_HEIGHT/4, 
                                 al_map_rgb(180, 180, 180)); 
    }
}
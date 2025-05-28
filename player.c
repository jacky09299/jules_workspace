#include "player.h"
#include "globals.h"   // For player, player_knife, bosses, camera_x, camera_y
#include "config.h"    // For various player and skill constants
#include "projectile.h"// For spawn_projectile
#include "utils.h"     // For calculate_distance_between_points, get_knife_path_point
#include <stdio.h>     // For printf
#include <math.h>      // For cos, sin, fmin

/**
 * 初始化玩家的屬性。
 */
void init_player() { // Changed return type to void, modifies global player
    player.hp = 10000;
    player.max_hp = 10000;
    player.strength = 10;
    player.magic = 15;
    player.speed = PLAYER_SPEED;
    player.money = 0;
    player.x = 0.0f;
    player.y = 0.0f;
    player.v_x = 0.0f;
    player.v_y = 0.0f;
    player.facing_angle = 0.0f;
    player.normal_attack_cooldown_timer = 0;

    for (int i = 0; i < MAX_PLAYER_SKILLS; ++i) {
        player.learned_skills[i] = SKILL_NONE;
        player.skill_cooldown_timers[i] = 0;
    }
    player.learned_skills[SKILL_WATER_ATTACK] = SKILL_WATER_ATTACK;
    player.learned_skills[SKILL_ICE_SHARD] = SKILL_ICE_SHARD;
    player.learned_skills[SKILL_LIGHTNING_BOLT] = SKILL_LIGHTNING_BOLT;
    player.learned_skills[SKILL_HEAL] = SKILL_HEAL;
    player.learned_skills[SKILL_FIREBALL] = SKILL_FIREBALL;
    for (int i = 0; i < NUM_ITEMS; ++i) {
        player.item_quantities[i] = 0;
    }

}

/**
 * 初始化玩家刀子攻擊的狀態。
 */
void init_player_knife() {
    player_knife.active = false;
    player_knife.path_progress_timer = 0.0f;
    for (int i = 0; i < MAX_BOSSES; ++i) {
        player_knife.hit_bosses_this_swing[i] = false;
    }
}

/**
 * 玩家執行普通攻擊 (現在是啟動刀子攻擊)。
 */
void player_perform_normal_attack() {
    if (player_knife.active || player.normal_attack_cooldown_timer > 0) {
        return;
    }
    player_knife.active = true;
    player_knife.path_progress_timer = 0.0f;
    player_knife.owner_start_x = player.x;
    player_knife.owner_start_y = player.y;
    player_knife.owner_start_facing_angle = player.facing_angle;
    for (int i = 0; i < MAX_BOSSES; ++i) {
        player_knife.hit_bosses_this_swing[i] = false;
    }
    player.normal_attack_cooldown_timer = PLAYER_NORMAL_ATTACK_COOLDOWN;
}

/**
 * 玩家使用水彈攻擊技能。
 */
void player_use_water_attack() {
    if (player.skill_cooldown_timers[SKILL_WATER_ATTACK] > 0) { 
        printf("水彈攻擊冷卻中 (%ds)\n", player.skill_cooldown_timers[SKILL_WATER_ATTACK]/FPS + 1);
        return;
    }
    player.skill_cooldown_timers[SKILL_WATER_ATTACK] = PLAYER_WATER_SKILL_COOLDOWN; 
    float projectile_target_x = player.x + cos(player.facing_angle) * 1000.0f;
    float projectile_target_y = player.y + sin(player.facing_angle) * 1000.0f;
    spawn_projectile(player.x, player.y, projectile_target_x, projectile_target_y,
                      OWNER_PLAYER, PROJ_TYPE_WATER, PLAYER_WATER_PROJECTILE_DAMAGE + player.magic, 
                      PLAYER_WATER_PROJECTILE_SPEED, PLAYER_WATER_PROJECTILE_LIFESPAN, -1);
    printf("玩家施放水彈攻擊！\n");
}

/**
 * 玩家使用冰錐術技能。
 */
void player_use_ice_shard() {
    if (player.skill_cooldown_timers[SKILL_ICE_SHARD] > 0) { 
        printf("冰錐術冷卻中 (%ds)\n", player.skill_cooldown_timers[SKILL_ICE_SHARD]/FPS + 1);
        return;
    }
    player.skill_cooldown_timers[SKILL_ICE_SHARD] = PLAYER_ICE_SKILL_COOLDOWN; 
    float projectile_target_x = player.x + cos(player.facing_angle) * 1000.0f;
    float projectile_target_y = player.y + sin(player.facing_angle) * 1000.0f;
    spawn_projectile(player.x, player.y, projectile_target_x, projectile_target_y,
                      OWNER_PLAYER, PROJ_TYPE_ICE, PLAYER_ICE_PROJECTILE_DAMAGE + player.magic, 
                      PLAYER_ICE_PROJECTILE_SPEED, PLAYER_ICE_PROJECTILE_LIFESPAN, -1);
    printf("玩家施放冰錐術！\n");
}

/**
 * 玩家使用閃電鏈技能。
 */
void player_use_lightning_bolt() {
    if (player.skill_cooldown_timers[SKILL_LIGHTNING_BOLT] > 0) { 
        printf("閃電鏈冷卻中 (%ds)\n", player.skill_cooldown_timers[SKILL_LIGHTNING_BOLT]/FPS + 1);
        return;
    }
    player.skill_cooldown_timers[SKILL_LIGHTNING_BOLT] = PLAYER_LIGHTNING_SKILL_COOLDOWN; 
    bool hit_any = false; 
    for (int i = 0; i < MAX_BOSSES; ++i) {
        if (bosses[i].is_alive) { 
            float dist = calculate_distance_between_points(player.x, player.y, bosses[i].x, bosses[i].y); 
            if (dist < PLAYER_LIGHTNING_RANGE) { 
                int damage_dealt = PLAYER_LIGHTNING_DAMAGE + player.magic; 
                bosses[i].hp -= damage_dealt; 
                printf("閃電鏈命中 Boss %d (原型 %d)！ Boss HP: %d/%d\n", bosses[i].id, bosses[i].archetype, bosses[i].hp, bosses[i].max_hp);
                hit_any = true;
                if (bosses[i].hp <= 0) { 
                    bosses[i].is_alive = false; 
                    printf("Boss %d (原型 %d) 被閃電鏈擊敗！\n", bosses[i].id, bosses[i].archetype);
                }
            }
        }
    }
    if (!hit_any) printf("閃電鏈：範圍內沒有 Boss！\n");
}

/**
 * 玩家使用治療術技能。
 */
void player_use_heal() {
    if (player.skill_cooldown_timers[SKILL_HEAL] > 0) { 
        printf("治療術冷卻中 (%ds)\n", player.skill_cooldown_timers[SKILL_HEAL]/FPS + 1);
        return;
    }
    player.skill_cooldown_timers[SKILL_HEAL] = PLAYER_HEAL_SKILL_COOLDOWN; 
    int old_hp = player.hp;
    player.hp += PLAYER_HEAL_AMOUNT + player.magic * 2; 
    if (player.hp > player.max_hp) player.hp = player.max_hp; 
    printf("玩家治療了 %d 點生命！ (%d -> %d)\n", player.hp - old_hp, old_hp, player.hp);
}

/**
 * 玩家使用火球術技能。
 */
void player_use_fireball() {
    if (player.skill_cooldown_timers[SKILL_FIREBALL] > 0) { 
        printf("火球術冷卻中 (%ds)\n", player.skill_cooldown_timers[SKILL_FIREBALL]/FPS + 1);
        return;
    }
    player.skill_cooldown_timers[SKILL_FIREBALL] = PLAYER_FIREBALL_SKILL_COOLDOWN; 
    float projectile_target_x = player.x + cos(player.facing_angle) * 1000.0f;
    float projectile_target_y = player.y + sin(player.facing_angle) * 1000.0f;
    spawn_projectile(player.x, player.y, projectile_target_x, projectile_target_y,
                      OWNER_PLAYER, PROJ_TYPE_PLAYER_FIREBALL, PLAYER_FIREBALL_DAMAGE + player.magic, 
                      PLAYER_FIREBALL_SPEED, PLAYER_FIREBALL_LIFESPAN, -1);
    printf("玩家施放火球術！\n");
}

/**
 * 更新玩家角色的狀態。
 */
void update_player_character() {
    player.x += player.v_x; 
    player.y += player.v_y; 

    for (int i = 0; i < MAX_PLAYER_SKILLS; ++i) {
        if (player.skill_cooldown_timers[i] > 0) {
            player.skill_cooldown_timers[i]--; 
        }
    }
}

/**
 * 更新玩家刀子攻擊的狀態。
 */
void update_player_knife() {
    if (!player_knife.active) {
        return;
    }

    player_knife.path_progress_timer += 1.0f;

    if (player_knife.path_progress_timer >= KNIFE_ATTACK_DURATION) {
        player_knife.active = false;
        return;
    }

    float progress = player_knife.path_progress_timer / KNIFE_ATTACK_DURATION; 
    float local_x, local_y, local_path_angle;
    get_knife_path_point(progress, &local_x, &local_y, &local_path_angle);

    float cos_a = cos(player_knife.owner_start_facing_angle);
    float sin_a = sin(player_knife.owner_start_facing_angle);

    float world_offset_x = local_x * cos_a - local_y * sin_a;
    float world_offset_y = local_x * sin_a + local_y * cos_a;

    player_knife.x = player_knife.owner_start_x + world_offset_x;
    player_knife.y = player_knife.owner_start_y + world_offset_y;
    player_knife.angle = player_knife.owner_start_facing_angle + local_path_angle;

    float knife_collision_radius = fmin(KNIFE_SPRITE_WIDTH, KNIFE_SPRITE_HEIGHT) / 3.0f;

    for (int i = 0; i < MAX_BOSSES; ++i) {
        if (bosses[i].is_alive && !player_knife.hit_bosses_this_swing[i]) {
            float dist = calculate_distance_between_points(player_knife.x, player_knife.y, bosses[i].x, bosses[i].y);
            if (dist < bosses[i].collision_radius + knife_collision_radius) {
                int damage_dealt = KNIFE_DAMAGE_BASE + player.strength - bosses[i].defense;
                if (damage_dealt < 1) damage_dealt = 1;
                
                bosses[i].hp -= damage_dealt;
                player_knife.hit_bosses_this_swing[i] = true; 

                printf("刀子擊中 Boss %d (原型 %d)！造成 %d 傷害。Boss HP: %d/%d\n",
                       bosses[i].id, bosses[i].archetype, damage_dealt, bosses[i].hp, bosses[i].max_hp);

                if (bosses[i].hp <= 0) {
                    bosses[i].is_alive = false;
                    printf("Boss %d (原型 %d) 被刀子擊敗！\n", bosses[i].id, bosses[i].archetype);
                }
            }
        }
    }
}

/**
 * 更新遊戲攝影機的位置。
 */
void update_game_camera() {
    camera_x = player.x - SCREEN_WIDTH / 2.0f;  
    camera_y = player.y - SCREEN_HEIGHT / 2.0f; 
}
#include "boss.h"
#include "globals.h"    // For bosses array, player, boss_archetype_X_sprite_asset
#include "config.h"     // For boss related constants
#include "projectile.h" // For spawn_projectile
#include "utils.h"      // For calculate_distance_between_points
#include <stdio.h>      // For printf
#include <stdlib.h>     // For rand
#include <math.h>       // For M_PI, atan2, cos, sin

/**
 * 設定 Boss 的屬性、圖像資源和特定行為參數。
 */
void configure_boss_stats_and_assets(Boss* b, BossArchetype archetype, int difficulty_tier, int boss_id_for_cooldown_randomness) {
    b->max_hp = 60 + difficulty_tier * 30;
    b->strength = 10 + difficulty_tier * 4;
    b->speed = 1.8f + difficulty_tier * 0.05f;
    b->defense = 7 + difficulty_tier * 2;
    b->magic = 10 + difficulty_tier * 2;
    b->ranged_special_projectile_type = PROJ_TYPE_FIRE;

    switch (archetype) {
        case BOSS_TYPE_TANK:
            b->max_hp = (int)(b->max_hp * 2.5f);
            b->strength = (int)(b->strength * 1.0f);
            b->speed *= 0.75f;
            b->defense += 12 + difficulty_tier * 4;
            b->sprite_asset = boss_archetype_tank_sprite_asset;
            b->target_display_width = BOSS1_TARGET_WIDTH * 1.20f;
            b->target_display_height = BOSS1_TARGET_HEIGHT * 1.20f;
            if (!b->sprite_asset) { b->target_display_width = 70; b->target_display_height = 70;}
            b->ranged_special_ability_cooldown_timer = (rand() % (FPS * 2)) + BOSS_RANGED_SPECIAL_ABILITY_BASE_COOLDOWN + (FPS * (boss_id_for_cooldown_randomness % 2));
            b->melee_primary_ability_cooldown_timer = (rand() % FPS) + BOSS_MELEE_PRIMARY_ABILITY_BASE_COOLDOWN;
            break;
        case BOSS_TYPE_SKILLFUL:
            b->max_hp = (int)(b->max_hp * 1.1f);
            b->strength = (int)(b->strength * 0.75f);
            b->speed *= 1.1f;
            b->defense = (b->defense - 3 > 1) ? b->defense - 3 : 1;
            b->magic = (int)(b->magic * 1.5f);
            b->sprite_asset = boss_archetype_skillful_sprite_asset;
            b->target_display_width = BOSS2_TARGET_WIDTH;
            b->target_display_height = BOSS2_TARGET_HEIGHT;
            if (!b->sprite_asset) { b->target_display_width = 40; b->target_display_height = 40;}
            b->ranged_special_ability_cooldown_timer = (rand() % (FPS / 2)) + (int)(BOSS_RANGED_SPECIAL_ABILITY_BASE_COOLDOWN * 0.35f) + (FPS/2 * (boss_id_for_cooldown_randomness % 2));
            b->melee_primary_ability_cooldown_timer = (rand() % FPS) + (int)(BOSS_MELEE_PRIMARY_ABILITY_BASE_COOLDOWN * 1.35f);
            break;
        case BOSS_TYPE_BERSERKER:
            b->max_hp = (int)(b->max_hp * 1.5f);
            b->strength = (int)(b->strength * 2.2f);
            b->speed *= 0.50f;
            b->defense += 1 + difficulty_tier;
            b->sprite_asset = boss_archetype_berserker_sprite_asset ? boss_archetype_berserker_sprite_asset : (boss_archetype_tank_sprite_asset ? boss_archetype_tank_sprite_asset : NULL);
            b->target_display_width = boss_archetype_berserker_sprite_asset ? BOSS3_TARGET_WIDTH : (boss_archetype_tank_sprite_asset ? BOSS1_TARGET_WIDTH : 60);
            b->target_display_height = boss_archetype_berserker_sprite_asset ? BOSS3_TARGET_HEIGHT : (boss_archetype_tank_sprite_asset ? BOSS1_TARGET_HEIGHT : 60);
            b->ranged_special_ability_cooldown_timer = (rand() % (FPS * 2)) + (int)(BOSS_RANGED_SPECIAL_ABILITY_BASE_COOLDOWN * 1.5f) + (FPS * (boss_id_for_cooldown_randomness % 2));
            b->melee_primary_ability_cooldown_timer = (rand() % (FPS / 2)) + (int)(BOSS_MELEE_PRIMARY_ABILITY_BASE_COOLDOWN * 0.55f);
            break;
    }
    b->hp = b->max_hp;
    b->collision_radius = b->target_display_width / 2.0f;
}

/**
 * 根據預設的原型數量初始化所有 Boss。
 */
void init_bosses_by_archetype() {
    const int num_tanks = 3;
    const int num_skillful = 1;
    const int num_berserkers = 2;
    int current_boss_idx = 0;
    float initial_x_pos = 200.0f;
    float x_spacing = 170.0f;
    float initial_y_pos = 150.0f;
    float y_spacing_per_row = 120.0f;
    int bosses_per_row = 3;

    for (int i = 0; i < num_tanks; ++i) {
        if (current_boss_idx >= MAX_BOSSES) break;
        Boss* b = &bosses[current_boss_idx];
        b->id = current_boss_idx;
        b->archetype = BOSS_TYPE_TANK;
        int difficulty_tier = current_boss_idx / bosses_per_row;
        configure_boss_stats_and_assets(b, BOSS_TYPE_TANK, difficulty_tier, b->id);
        b->x = initial_x_pos + (current_boss_idx % bosses_per_row) * x_spacing;
        b->y = initial_y_pos + (current_boss_idx / bosses_per_row) * y_spacing_per_row;
        b->v_x = 0.0f; b->v_y = 0.0f; b->facing_angle = M_PI / 2.0; b->is_alive = true;
        b->current_ability_in_use = BOSS_ABILITY_MELEE_PRIMARY;
        current_boss_idx++;
    }

    for (int i = 0; i < num_skillful; ++i) {
        if (current_boss_idx >= MAX_BOSSES) break;
        Boss* b = &bosses[current_boss_idx];
        b->id = current_boss_idx;
        b->archetype = BOSS_TYPE_SKILLFUL;
        int difficulty_tier = current_boss_idx / bosses_per_row;
        configure_boss_stats_and_assets(b, BOSS_TYPE_SKILLFUL, difficulty_tier, b->id);
        b->x = initial_x_pos + (current_boss_idx % bosses_per_row) * x_spacing;
        b->y = initial_y_pos + (current_boss_idx / bosses_per_row) * y_spacing_per_row;
        b->v_x = 0.0f; b->v_y = 0.0f; b->facing_angle = M_PI / 2.0; b->is_alive = true;
        b->current_ability_in_use = BOSS_ABILITY_MELEE_PRIMARY;
        current_boss_idx++;
    }

    for (int i = 0; i < num_berserkers; ++i) {
        if (current_boss_idx >= MAX_BOSSES) break;
        Boss* b = &bosses[current_boss_idx];
        b->id = current_boss_idx;
        b->archetype = BOSS_TYPE_BERSERKER;
        int difficulty_tier = current_boss_idx / bosses_per_row;
        configure_boss_stats_and_assets(b, BOSS_TYPE_BERSERKER, difficulty_tier, b->id);
        b->x = initial_x_pos + (current_boss_idx % bosses_per_row) * x_spacing;
        b->y = initial_y_pos + (current_boss_idx / bosses_per_row) * y_spacing_per_row;
        b->v_x = 0.0f; b->v_y = 0.0f; b->facing_angle = M_PI / 2.0; b->is_alive = true;
        b->current_ability_in_use = BOSS_ABILITY_MELEE_PRIMARY;
        current_boss_idx++;
    }
    
    for (int i = current_boss_idx; i < MAX_BOSSES; ++i) {
        bosses[i].is_alive = false;
    }
}

/**
 * Boss 評估當前狀況並執行相應的動作。
 */
void boss_evaluate_and_execute_action(Boss* b) {
    if (!b->is_alive) return; 

    float dist_to_player = calculate_distance_between_points(b->x, b->y, player.x, player.y); 
    bool attempt_ranged_special = false; 
    int ranged_special_usage_chance = 20; 

    if (b->archetype == BOSS_TYPE_SKILLFUL) {
        ranged_special_usage_chance = 55; 
    } else if (b->archetype == BOSS_TYPE_BERSERKER) {
        ranged_special_usage_chance = 10; 
    }

    if ((rand() % 100) < ranged_special_usage_chance) { 
        attempt_ranged_special = true;
    }

    if (b->ranged_special_ability_cooldown_timer <= 0 && dist_to_player < 600 && attempt_ranged_special) { 
        b->current_ability_in_use = BOSS_ABILITY_RANGED_SPECIAL; 
        
        int current_ranged_special_damage = BOSS_RANGED_SPECIAL_BASE_DAMAGE + b->magic; 
        if (b->archetype == BOSS_TYPE_SKILLFUL) {
            current_ranged_special_damage = (int)(current_ranged_special_damage * 1.4f); 
        } else if (b->archetype == BOSS_TYPE_BERSERKER) {
            current_ranged_special_damage = (int)(current_ranged_special_damage * 0.7f); 
        }

        spawn_projectile(b->x, b->y, player.x, player.y, 
                          OWNER_BOSS, b->ranged_special_projectile_type, current_ranged_special_damage,
                          BOSS_RANGED_SPECIAL_PROJECTILE_BASE_SPEED, BOSS_RANGED_SPECIAL_PROJECTILE_BASE_LIFESPAN, b->id);
        
        if (b->archetype == BOSS_TYPE_SKILLFUL) {
            b->ranged_special_ability_cooldown_timer = (int)(BOSS_RANGED_SPECIAL_ABILITY_BASE_COOLDOWN * 0.45f); 
        } else if (b->archetype == BOSS_TYPE_BERSERKER) {
            b->ranged_special_ability_cooldown_timer = (int)(BOSS_RANGED_SPECIAL_ABILITY_BASE_COOLDOWN * 1.6f); 
        } else { 
            b->ranged_special_ability_cooldown_timer = BOSS_RANGED_SPECIAL_ABILITY_BASE_COOLDOWN;
        }
        printf("Boss %d (原型 %d) 使用遠程特殊技能 (類型: %d)！傷害: %d\n", b->id, b->archetype, b->ranged_special_projectile_type, current_ranged_special_damage);
        b->melee_primary_ability_cooldown_timer += FPS * 0.25; 
        return; 
    }

    float effective_melee_range = BOSS_MELEE_PRIMARY_BASE_RANGE;
     if (b->archetype == BOSS_TYPE_BERSERKER) {
        effective_melee_range *= 1.1f; 
    }

    if (b->melee_primary_ability_cooldown_timer <= 0 && dist_to_player < (effective_melee_range + b->collision_radius + PLAYER_SPRITE_SIZE)) { 
        b->current_ability_in_use = BOSS_ABILITY_MELEE_PRIMARY; 
        int damage_dealt = b->strength; 
        player.hp -= damage_dealt; 
        printf("Boss %d (原型 %d) 使用近戰主技能！玩家 HP: %d\n", b->id, b->archetype, player.hp);

        if (b->archetype == BOSS_TYPE_BERSERKER) {
            b->melee_primary_ability_cooldown_timer = (int)(BOSS_MELEE_PRIMARY_ABILITY_BASE_COOLDOWN * 0.50f); 
        } else if (b->archetype == BOSS_TYPE_SKILLFUL) {
            b->melee_primary_ability_cooldown_timer = (int)(BOSS_MELEE_PRIMARY_ABILITY_BASE_COOLDOWN * 1.45f); 
        } else { 
            b->melee_primary_ability_cooldown_timer = BOSS_MELEE_PRIMARY_ABILITY_BASE_COOLDOWN;
        }
        return; 
    }
    b->current_ability_in_use = BOSS_ABILITY_MELEE_PRIMARY; // Default action if nothing else
}

/**
 * 更新特定 Boss 角色的狀態。
 */
void update_boss_character(Boss* b) {
    if (!b->is_alive) { 
        b->v_x = 0; b->v_y = 0; 
        return;
    }

    if (b->ranged_special_ability_cooldown_timer > 0) b->ranged_special_ability_cooldown_timer--;
    if (b->melee_primary_ability_cooldown_timer > 0) b->melee_primary_ability_cooldown_timer--;

    float dist_to_player = calculate_distance_between_points(b->x, b->y, player.x, player.y); 
    b->v_x = 0; b->v_y = 0; 

    float engagement_distance_factor = 0.75f; 
    float base_engagement_range = BOSS_MELEE_PRIMARY_BASE_RANGE * (b->archetype == BOSS_TYPE_BERSERKER ? 1.1f : 1.0f); 
    float desired_distance = base_engagement_range * engagement_distance_factor;
                                   
    if (dist_to_player > 800 && b->archetype != BOSS_TYPE_SKILLFUL) { 
        // Stay put
    } else if (dist_to_player > desired_distance + b->collision_radius + PLAYER_SPRITE_SIZE) { 
        float angle_to_player = atan2(player.y - b->y, player.x - b->x); 
        b->facing_angle = angle_to_player; 
        b->v_x = cos(angle_to_player) * b->speed; 
        b->v_y = sin(angle_to_player) * b->speed; 
    } else if (b->archetype == BOSS_TYPE_SKILLFUL && dist_to_player < desired_distance * 0.8f && dist_to_player > 100) { 
        // Skillful boss tries to maintain some distance
        float angle_to_player = atan2(player.y - b->y, player.x - b->x); 
        b->facing_angle = angle_to_player; 
        b->v_x = -cos(angle_to_player) * b->speed * 0.6f; 
        b->v_y = -sin(angle_to_player) * b->speed * 0.6f;
    }

    b->x += b->v_x; 
    b->y += b->v_y; 

    boss_evaluate_and_execute_action(b); 
}
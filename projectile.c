#include "projectile.h"
#include "globals.h" // For projectiles array, player, bosses
#include "utils.h"   // For calculate_distance_between_points
#include "config.h"  // For MAX_PROJECTILES, PROJECTILE_RADIUS, PLAYER_SPRITE_SIZE
#include <stdio.h>   // For printf
#include <math.h>    // For atan2, cos, sin

/**
 * @brief 初始化投射物陣列。
 */
void init_projectiles() {
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        projectiles[i].active = false;
    }
}

/**
 * @brief 在投射物陣列中尋找一個未被使用的欄位。
 */
int find_inactive_projectile_slot() {
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (!projectiles[i].active) { 
            return i; 
        }
    }
    return -1; 
}

/**
 * @brief 生成一個新的投射物。
 */
void spawn_projectile(float origin_x, float origin_y, float target_x, float target_y, ProjectileOwner owner_type, ProjectileType proj_type, int base_damage, float travel_speed, int active_lifespan_frames, int owner_entity_id) {
    int slot = find_inactive_projectile_slot(); 
    if (slot == -1) return; 

    projectiles[slot].active = true;        
    projectiles[slot].x = origin_x;         
    projectiles[slot].y = origin_y;         
    projectiles[slot].owner = owner_type;   
    projectiles[slot].type = proj_type;     
    projectiles[slot].damage = base_damage; 
    projectiles[slot].lifespan = active_lifespan_frames; 
    projectiles[slot].owner_id = owner_entity_id; 

    float angle_rad = atan2(target_y - origin_y, target_x - origin_x); 
    projectiles[slot].v_x = cos(angle_rad) * travel_speed; 
    projectiles[slot].v_y = sin(angle_rad) * travel_speed; 
}

/**
 * @brief 更新所有活動中投射物的狀態。
 */
void update_active_projectiles() {
    for (int i = 0; i < MAX_PROJECTILES; ++i) {
        if (projectiles[i].active) { 
            projectiles[i].x += projectiles[i].v_x; 
            projectiles[i].y += projectiles[i].v_y; 
            projectiles[i].lifespan--;             

            if (projectiles[i].lifespan <= 0) { 
                projectiles[i].active = false;  
                continue; 
            }

            if (projectiles[i].owner == OWNER_PLAYER) { 
                for (int j = 0; j < MAX_BOSSES; ++j) {
                    if (bosses[j].is_alive && 
                        calculate_distance_between_points(projectiles[i].x, projectiles[i].y, bosses[j].x, bosses[j].y) < bosses[j].collision_radius + PROJECTILE_RADIUS) {
                        
                        int damage_dealt = projectiles[i].damage - bosses[j].defense; 
                        if (damage_dealt < 1 && projectiles[i].damage > 0) damage_dealt = 1; 
                        else if (projectiles[i].damage <= 0) damage_dealt = 0; 

                        if (damage_dealt > 0) bosses[j].hp -= damage_dealt; 

                        printf("玩家投射物 (傷害: %d, 類型: %d) 命中 Boss %d (原型 %d)！ Boss HP: %d/%d\n", projectiles[i].damage, projectiles[i].type, bosses[j].id, bosses[j].archetype, bosses[j].hp, bosses[j].max_hp);
                        projectiles[i].active = false; 
                        if (bosses[j].hp <= 0) { 
                            bosses[j].is_alive = false;
                            printf("Boss %d (原型 %d) 被投射物擊敗！\n", bosses[j].id, bosses[j].archetype);
                        }
                        break; 
                    }
                }
            } else if (projectiles[i].owner == OWNER_BOSS) { 
                if (calculate_distance_between_points(projectiles[i].x, projectiles[i].y, player.x, player.y) < PLAYER_SPRITE_SIZE + PROJECTILE_RADIUS) {
                    int damage_taken = projectiles[i].damage;
                    if (damage_taken < 0) damage_taken = 0; 
                    player.hp -= damage_taken; 
                    printf("玩家被 Boss %d 的投射物 (傷害: %d, 類型: %d) 擊中！玩家 HP: %d\n", projectiles[i].owner_id, projectiles[i].damage, projectiles[i].type, player.hp);
                    projectiles[i].active = false; 
                }
            }
        }
    }
}
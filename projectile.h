#ifndef PROJECTILE_H
#define PROJECTILE_H

#include "types.h" // For Projectile, ProjectileOwner, ProjectileType

void init_projectiles(void);
int find_inactive_projectile_slot(void);
void spawn_projectile(float origin_x, float origin_y, float target_x, float target_y, 
                      ProjectileOwner owner_type, ProjectileType proj_type, 
                      int base_damage, float travel_speed, 
                      int active_lifespan_frames, int owner_entity_id);
void update_active_projectiles(void);

#endif // PROJECTILE_H
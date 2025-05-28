#ifndef BOSS_H
#define BOSS_H

#include "types.h" // For Boss, BossArchetype

void configure_boss_stats_and_assets(Boss* b, BossArchetype archetype, int difficulty_tier, int boss_id_for_cooldown_randomness);
void init_bosses_by_archetype(void);
void boss_evaluate_and_execute_action(Boss* b);
void update_boss_character(Boss* b);

#endif // BOSS_H
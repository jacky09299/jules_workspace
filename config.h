#ifndef CONFIG_H
#define CONFIG_H

// 螢幕尺寸定義
#define SCREEN_WIDTH 1000                   // 螢幕寬度
#define SCREEN_HEIGHT 1000                  // 螢幕高度
#define FPS 60                              // 遊戲幀率 (Frames Per Second)
#ifndef M_PI // 如果 M_PI 未定義 (例如在某些 Windows 編譯器上)
#define M_PI 3.14159265358979323846       // 圓周率 PI
#endif

// 目標圖像尺寸定義
#define PLAYER_TARGET_WIDTH 50              // 玩家圖像目標寬度
#define PLAYER_TARGET_HEIGHT 50             // 玩家圖像目標高度
#define BOSS1_TARGET_WIDTH 60               // Boss 1 (坦克型) 圖像目標寬度
#define BOSS1_TARGET_HEIGHT 60              // Boss 1 (坦克型) 圖像目標高度
#define BOSS2_TARGET_WIDTH 40               // Boss 2 (技巧型) 圖像目標寬度
#define BOSS2_TARGET_HEIGHT 40              // Boss 2 (技巧型) 圖像目標高度
#define BOSS3_TARGET_WIDTH 70               // Boss 3 (狂戰型) 圖像目標寬度
#define BOSS3_TARGET_HEIGHT 70              // Boss 3 (狂戰型) 圖像目標高度

#define PLAYER_SPRITE_SIZE (PLAYER_TARGET_WIDTH / 2) // 玩家圖像碰撞半徑 (基於寬度)
#define PLAYER_SPEED 8.0f                   // 玩家移動速度

#define MAX_BOSSES 6                        // 最大 Boss 數量 (3 坦克, 1 技巧, 2 狂戰)
#define MAX_PLAYER_SKILLS 6                 // 玩家最大技能數量

// 玩家技能常數
#define PLAYER_WATER_PROJECTILE_DAMAGE 25   // 水彈基礎傷害
#define PLAYER_WATER_PROJECTILE_SPEED 10.0f // 水彈飛行速度
#define PLAYER_WATER_PROJECTILE_LIFESPAN (FPS * 2) // 水彈持續時間 (幀)
#define PLAYER_WATER_SKILL_COOLDOWN (FPS * 5)  // 水彈技能冷卻時間 (幀)
#define PLAYER_ICE_PROJECTILE_DAMAGE 35     // 冰錐基礎傷害
#define PLAYER_ICE_PROJECTILE_SPEED 8.0f    // 冰錐飛行速度
#define PLAYER_ICE_PROJECTILE_LIFESPAN (FPS * 3) // 冰錐持續時間 (幀)
#define PLAYER_ICE_SKILL_COOLDOWN (FPS * 7)    // 冰錐技能冷卻時間 (幀)
#define PLAYER_LIGHTNING_DAMAGE 50          // 閃電鏈基礎傷害
#define PLAYER_LIGHTNING_RANGE 150.0f       // 閃電鏈作用範圍
#define PLAYER_LIGHTNING_SKILL_COOLDOWN (FPS * 10) // 閃電鏈技能冷卻時間 (幀)
#define PLAYER_HEAL_AMOUNT 30               // 治療術基礎治療量
#define PLAYER_HEAL_SKILL_COOLDOWN (FPS * 15)  // 治療術技能冷卻時間 (幀)
#define PLAYER_FIREBALL_DAMAGE 40           // 火球術基礎傷害
#define PLAYER_FIREBALL_SPEED 12.0f         // 火球術飛行速度
#define PLAYER_FIREBALL_LIFESPAN (FPS * 2.5) // 火球術持續時間 (幀)
#define PLAYER_FIREBALL_SKILL_COOLDOWN (FPS * 6) // 火球術技能冷卻時間 (幀)

// 道具最大數量
#define NUM_ITEMS 5

// Boss 技能常數
#define BOSS_MELEE_PRIMARY_BASE_RANGE 80.0f // Boss 近戰主技能基礎範圍
#define BOSS_RANGED_SPECIAL_BASE_DAMAGE 20  // Boss 遠程特殊技能基礎傷害
#define BOSS_RANGED_SPECIAL_PROJECTILE_BASE_SPEED 7.0f // Boss 遠程特殊投射物基礎速度
#define BOSS_RANGED_SPECIAL_PROJECTILE_BASE_LIFESPAN (FPS * 2.5) // Boss 遠程特殊投射物基礎持續時間 (幀)
#define BOSS_RANGED_SPECIAL_ABILITY_BASE_COOLDOWN (FPS * 6) // Boss 遠程特殊技能基礎冷卻時間 (幀)
#define BOSS_MELEE_PRIMARY_ABILITY_BASE_COOLDOWN (FPS * 1.5) // Boss 近戰主技能基礎冷卻時間 (幀)

// 投射物常數
#define MAX_PROJECTILES 50                  // 最大投射物數量
#define PROJECTILE_RADIUS 8                 // 投射物碰撞半徑

// 刀子攻擊常數
#define KNIFE_SPRITE_WIDTH 80               // 刀子圖像期望顯示寬度
#define KNIFE_SPRITE_HEIGHT 80              // 刀子圖像期望顯示高度
#define KNIFE_ATTACK_DURATION (FPS * 0.3f)  // 刀子攻擊動畫持續時間 (幀) (例如 0.6 秒)
#define PLAYER_NORMAL_ATTACK_COOLDOWN (FPS * 0.3f) // 玩家普攻冷卻時間 (幀) (例如 1 秒)
#define KNIFE_DAMAGE_BASE 15                // 刀子基礎傷害 (會加上玩家力量)

#define MAX_GROWTH_BUTTONS 5            // 養成畫面按鈕數量

#endif // CONFIG_H
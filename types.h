#ifndef TYPES_H
#define TYPES_H

#include <stdbool.h>
#include <allegro5/allegro.h> // For ALLEGRO_COLOR
#include "config.h" // For MAX_PLAYER_SKILLS, MAX_BOSSES

// 遊戲階段枚舉
typedef enum {
    MENU,       // 主選單階段
    EXIT,       // 退出遊戲
    GROWTH,     // 養成階段
    MINIGAME1,  // 小遊戲1
    MINIGAME2,  // 小遊戲2
    LOTTERY,      // 抽獎
    BACKPACK,   // 背包
    BATTLE      // 戰鬥階段
} GamePhase;

// 玩家技能標識符枚舉
typedef enum {
    SKILL_NONE,             // 無技能
    SKILL_WATER_ATTACK,     // 水彈攻擊
    SKILL_ICE_SHARD,        // 冰錐術
    SKILL_LIGHTNING_BOLT,   // 閃電鏈
    SKILL_HEAL,             // 治療術
    SKILL_FIREBALL          // 火球術
} PlayerSkillIdentifier;

// 玩家背包裡的道具
typedef enum {
    ITEM_HEALTH_POTION,
    ITEM_BOMB
} ItemType;

// Boss 技能標識符枚舉
typedef enum {
    BOSS_ABILITY_MELEE_PRIMARY, // Boss 近戰主技能
    BOSS_ABILITY_RANGED_SPECIAL // Boss 遠程特殊技能
} BossAbilityIdentifier;

// Boss 原型枚舉
typedef enum {
    BOSS_TYPE_TANK,         // 坦克型 Boss
    BOSS_TYPE_SKILLFUL,     // 技巧型 Boss
    BOSS_TYPE_BERSERKER     // 狂戰型 Boss
} BossArchetype;

// 投射物擁有者枚舉
typedef enum {
    OWNER_PLAYER,           // 投射物屬於玩家
    OWNER_BOSS              // 投射物屬於 Boss
} ProjectileOwner;

// 投射物類型枚舉
typedef enum {
    PROJ_TYPE_GENERIC,          // 通用類型 (預設或未使用)
    PROJ_TYPE_WATER,            // 水系投射物
    PROJ_TYPE_FIRE,             // 火系投射物 (通常為 Boss)
    PROJ_TYPE_ICE,              // 冰系投射物
    PROJ_TYPE_PLAYER_FIREBALL   // 玩家火球術
} ProjectileType;

// 投射物結構
typedef struct {
    float x, y;                 // 投射物當前位置 (x, y 座標)
    float v_x, v_y;             // 投射物速度向量 (x, y 分量)
    bool active;                // 投射物是否啟用 (是否在畫面中移動和碰撞)
    ProjectileOwner owner;      // 投射物擁有者 (玩家或 Boss)
    ProjectileType type;        // 投射物類型 (影響外觀、效果等)
    int damage;                 // 投射物造成的傷害值
    int lifespan;               // 投射物剩餘壽命 (幀數)，為0時消失
    int owner_id;               // 若擁有者是 Boss，則為 Boss 的 ID
} Projectile;

// 玩家結構
typedef struct {
    int hp;                     // 當前生命值
    int max_hp;                 // 最大生命值
    int strength;               // 力量 (影響物理傷害)
    int magic;                  // 魔力 (影響技能傷害或效果)
    float speed;                // 移動速度
    int money;                  // 金錢
    float x, y;                 // 玩家當前位置 (x, y 座標)
    float v_x, v_y;             // 玩家當前速度向量 (用於移動計算)
    float facing_angle;         // 玩家面朝角度 (弧度)
    PlayerSkillIdentifier learned_skills[MAX_PLAYER_SKILLS]; // 已學習的技能列表
    int skill_cooldown_timers[MAX_PLAYER_SKILLS]; // 各技能的冷卻計時器 (幀)
    int normal_attack_cooldown_timer; // 普通攻擊冷卻計時器
    int item_quantities[NUM_ITEMS]; //記錄每種道具的數量
} Player;

// Boss 結構
typedef struct {
    int id;                     // Boss 的唯一標識符
    BossArchetype archetype;    // Boss 的原型 (坦克、技巧、狂戰)
    int hp;                     // 當前生命值
    int max_hp;                 // 最大生命值
    int strength;               // 力量 (影響物理傷害)
    BossAbilityIdentifier current_ability_in_use; // 當前正在使用的技能
    int defense;                // 防禦力 (減免受到的物理傷害)
    int magic;                  // 魔力 (影響技能傷害或效果)
    float speed;                // 移動速度
    float x, y;                 // Boss 當前位置 (x, y 座標)
    float v_x, v_y;             // Boss 當前速度向量 (用於移動計算)
    float facing_angle;         // Boss 面朝角度 (弧度)
    int ranged_special_ability_cooldown_timer; // 遠程特殊技能冷卻計時器 (幀)
    int melee_primary_ability_cooldown_timer;  // 近戰主技能冷卻計時器 (幀)
    ProjectileType ranged_special_projectile_type; // 遠程特殊技能的投射物類型
    bool is_alive;              // Boss 是否存活
    ALLEGRO_BITMAP *sprite_asset; // Boss 的圖像資源
    float target_display_width; // Boss 圖像的目標顯示寬度
    float target_display_height;// Boss 圖像的目標顯示高度
    float collision_radius;     // Boss 的碰撞半徑
} Boss;

// 按鈕結構 (用於主選單和養成畫面)
typedef struct {
    float x, y, width, height;  // 按鈕的位置和尺寸
    const char* text;           // 按鈕上顯示的文字
    GamePhase action_phase;     // 按下按鈕後轉換到的遊戲階段 (或用於標識按鈕類型)
    ALLEGRO_COLOR color;        // 按鈕正常狀態顏色
    ALLEGRO_COLOR hover_color;  // 按鈕滑鼠懸停時顏色
    ALLEGRO_COLOR text_color;   // 按鈕文字顏色
    bool is_hovered;            // 滑鼠是否懸停在按鈕上
} Button;

// 玩家刀子攻擊狀態結構
typedef struct {
    bool active;                // 是否正在進行攻擊
    float x, y;                 // 刀子目前在世界座標系中的位置
    float angle;                // 刀子目前的旋轉角度 (世界座標系)
    float path_progress_timer;  // 路徑進度計時器 (0 到 KNIFE_ATTACK_DURATION)
    
    // 攻擊發起時玩家的狀態，用於計算路徑的基準點
    float owner_start_x;
    float owner_start_y;
    float owner_start_facing_angle;

    // 追蹤在此次揮砍中已擊中的 Boss，避免重複傷害
    bool hit_bosses_this_swing[MAX_BOSSES]; 
} PlayerKnifeState;

//逃跑門結構
typedef struct {
    float x, y;
    float width, height;
    bool is_active;
    bool is_counting_down;
    int countdown_frames; // 倒數用的 frame 數
} EscapeGate;

#endif // TYPES_H
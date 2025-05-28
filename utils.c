#include "utils.h"
#include "config.h" // For M_PI if needed by get_knife_path_point

/**
 * @brief 計算兩點之間的直線距離。
 */
float calculate_distance_between_points(float x1, float y1, float x2, float y2) {
    float dx = x2 - x1; 
    float dy = y2 - y1; 
    return sqrtf(dx * dx + dy * dy); 
}

/**
 * @brief 根據進度獲取刀子在其局部路徑上的位置和切線角度。
 */
void get_knife_path_point(float progress, float* local_x, float* local_y, float* local_angle) {
    float amplitude_x = 70.0f; 
    float amplitude_y = 45.0f;  
    
    float t_y = progress * 2.0f * M_PI;
    *local_y = amplitude_y * sin(t_y - M_PI/2.0f); 

    float t_x = progress * M_PI;
    *local_x = 20.0f + amplitude_x * sin(t_x); 

    float epsilon = 0.001f; 
    float next_prog = fminf(1.0f, progress + epsilon);
    float prev_prog = fmaxf(0.0f, progress - epsilon);

    float x_next, y_next, x_prev, y_prev;

    t_y = next_prog * 2.0f * M_PI;
    y_next = amplitude_y * sin(t_y - M_PI/2.0f);
    t_x = next_prog * M_PI;
    x_next = 20.0f + amplitude_x * sin(t_x);

    t_y = prev_prog * 2.0f * M_PI;
    y_prev = amplitude_y * sin(t_y - M_PI/2.0f);
    t_x = prev_prog * M_PI;
    x_prev = 20.0f + amplitude_x * sin(t_x);
    
    float delta_x = x_next - x_prev;
    float delta_y = y_next - y_prev;

    if (fabs(delta_x) < 0.0001f && fabs(delta_y) < 0.0001f) {
        if (progress < 0.5f) {
             *local_angle = atan2(amplitude_y * cos(0 - M_PI/2.0f) * 2.0 * M_PI, amplitude_x * cos(0) * M_PI); 
        } else {
             *local_angle = atan2(amplitude_y * cos(2*M_PI - M_PI/2.0f) * 2.0 * M_PI, amplitude_x * cos(M_PI) * M_PI);
        }
    } else {
        *local_angle = atan2(delta_y, delta_x);
    }
}
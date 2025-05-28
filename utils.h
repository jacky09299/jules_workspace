#ifndef UTILS_H
#define UTILS_H

#include <math.h>

float calculate_distance_between_points(float x1, float y1, float x2, float y2);
void get_knife_path_point(float progress, float* local_x, float* local_y, float* local_angle);

#endif // UTILS_H
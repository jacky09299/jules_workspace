#include <allegro5/allegro_primitives.h>
#include <allegro5/allegro_font.h>
#include <allegro5/allegro_ttf.h> // Though font is global, good practice
#include <stdio.h> // For printf during development
#include <math.h> // For sin and cos
#include <stdlib.h> // For rand()
#include <time.h>   // For time() in srand()

#ifdef _WIN32
#include <windows.h>
#include <mmsystem.h>
#endif

#include "globals.h"
#include "minigame1.h"
#include "types.h" // Included by globals.h or minigame1.h, good for clarity

// Audio Recording Constants (common)
#define AUDIO_BUFFER_SIZE (44100 * 2 * 35) // Approx 35 seconds of stereo audio at 44.1kHz, 16-bit. Using 2 for bytes per sample.
#define AUDIO_SAMPLE_RATE 44100
#define AUDIO_CHANNELS 1 // Mono
#define AUDIO_BITS_PER_SAMPLE 16

// Static global variables for audio recording
#ifdef _WIN32
static HWAVEIN hWaveIn = NULL;
static WAVEHDR waveHdr;
static char* pWaveBuffer = NULL; // Actual buffer for waveInPrepareHeader
static DWORD recordingStartTime = 0; // Windows specific time
#else
static time_t recordingStartTime_nonWin = 0; // For non-Windows time
static char* pWaveBuffer_nonWin = NULL; // Placeholder buffer for non-Windows
#endif
static bool isActuallyRecording = false; // Common flag
static bool displayPleaseSingMessage = false; // Common flag
static float audioLengthSeconds = 0.0f; // Common flag
static bool decibelsOkay = false; // Common flag

// Test flags for non-Windows audio simulation
static bool force_audio_too_short_for_test = false; 
static bool force_audio_too_quiet_for_test = false;


// Forward declarations for audio functions
static void prepare_audio_recording(void);
static void start_actual_audio_recording(void);
static bool stop_actual_audio_recording(void);
static void cleanup_audio_recording(void);


// Static global variables for the minigame
static MinigameFlowerPlant flower_plant;
static Button minigame_buttons[NUM_MINIGAME1_BUTTONS];
static bool seed_planted = false;
static bool is_singing = false;
static const int songs_to_flower = 8;
static bool minigame_srand_called = false; // Ensure srand is called only once for this minigame context

void init_minigame1(void) {
    if (!minigame_srand_called) {
        srand(time(NULL)); // Initialize random seed
        minigame_srand_called = true;
    }
    
    // Reset test flags
    force_audio_too_short_for_test = false;
    force_audio_too_quiet_for_test = false;
    
    cleanup_audio_recording(); // Clean up any previous audio resources
    prepare_audio_recording(); // Prepare audio for new session

    flower_plant.songs_sung = 0;
    flower_plant.growth_stage = 0;
    seed_planted = false;
    is_singing = false;
    // simulated_sound_detected = true; // This should be removed or commented out

    displayPleaseSingMessage = false;
    audioLengthSeconds = 0.0f;
    decibelsOkay = false;

    printf("DEBUG: Minigame Flower initialized/reset.\n");

    float button_width = 200;
    float button_height = 50;
    float center_x = SCREEN_WIDTH / 2.0f - button_width / 2.0f;

    // Button 0: "種下種子" (Plant Seed)
    minigame_buttons[0].x = center_x;
    minigame_buttons[0].y = SCREEN_HEIGHT - 200;
    minigame_buttons[0].width = button_width;
    minigame_buttons[0].height = button_height;
    minigame_buttons[0].text = "種下種子";
    minigame_buttons[0].color = al_map_rgb(70, 170, 70);
    minigame_buttons[0].hover_color = al_map_rgb(100, 200, 100);
    minigame_buttons[0].text_color = al_map_rgb(255, 255, 255);
    minigame_buttons[0].action_phase = MINIGAME1; // Or a dummy/specific action
    minigame_buttons[0].is_hovered = false;

    // Button 1: "開始唱歌" (Start Singing)
    minigame_buttons[1].x = center_x;
    minigame_buttons[1].y = SCREEN_HEIGHT - 200; // Same position, shown conditionally
    minigame_buttons[1].width = button_width;
    minigame_buttons[1].height = button_height;
    minigame_buttons[1].text = "開始唱歌";
    minigame_buttons[1].color = al_map_rgb(70, 70, 170);
    minigame_buttons[1].hover_color = al_map_rgb(100, 100, 200);
    minigame_buttons[1].text_color = al_map_rgb(255, 255, 255);
    minigame_buttons[1].action_phase = MINIGAME1;
    minigame_buttons[1].is_hovered = false;

    // Button 2: "重新開始" (Restart) - Appears with "Finish Singing"
    minigame_buttons[2].x = center_x - button_width / 2 - 10; // Left of center
    minigame_buttons[2].y = SCREEN_HEIGHT - 200;
    minigame_buttons[2].width = button_width;
    minigame_buttons[2].height = button_height;
    minigame_buttons[2].text = "重新開始";
    minigame_buttons[2].color = al_map_rgb(170, 70, 70);
    minigame_buttons[2].hover_color = al_map_rgb(200, 100, 100);
    minigame_buttons[2].text_color = al_map_rgb(255, 255, 255);
    minigame_buttons[2].action_phase = MINIGAME1;
    minigame_buttons[2].is_hovered = false;

    // Button 3: "完成歌唱" (Finish Singing) - Appears with "Restart"
    minigame_buttons[3].x = center_x + button_width / 2 + 10; // Right of center
    minigame_buttons[3].y = SCREEN_HEIGHT - 200;
    minigame_buttons[3].width = button_width;
    minigame_buttons[3].height = button_height;
    minigame_buttons[3].text = "完成歌唱";
    minigame_buttons[3].color = al_map_rgb(70, 170, 170);
    minigame_buttons[3].hover_color = al_map_rgb(100, 200, 200);
    minigame_buttons[3].text_color = al_map_rgb(255, 255, 255);
    minigame_buttons[3].action_phase = MINIGAME1;
    minigame_buttons[3].is_hovered = false;
    
    // Button 4: "離開小遊戲" (Exit Minigame)
    minigame_buttons[4].width = 150; // Slightly smaller
    minigame_buttons[4].height = 40;
    minigame_buttons[4].x = SCREEN_WIDTH - minigame_buttons[4].width - 20;
    minigame_buttons[4].y = SCREEN_HEIGHT - minigame_buttons[4].height - 20;
    minigame_buttons[4].text = "離開小遊戲";
    minigame_buttons[4].color = al_map_rgb(100, 100, 100);
    minigame_buttons[4].hover_color = al_map_rgb(130, 130, 130);
    minigame_buttons[4].text_color = al_map_rgb(255, 255, 255);
    minigame_buttons[4].action_phase = GROWTH; // This will trigger phase change
    minigame_buttons[4].is_hovered = false;

    // Button 5: "採收" (Harvest)
    minigame_buttons[5].x = center_x;
    minigame_buttons[5].y = SCREEN_HEIGHT - 200; // Same position as Start Singing
    minigame_buttons[5].width = button_width;
    minigame_buttons[5].height = button_height;
    minigame_buttons[5].text = "採收";
    minigame_buttons[5].color = al_map_rgb(200, 150, 50);
    minigame_buttons[5].hover_color = al_map_rgb(230, 180, 80);
    minigame_buttons[5].text_color = al_map_rgb(255, 255, 255);
    minigame_buttons[5].action_phase = MINIGAME1;
    minigame_buttons[5].is_hovered = false;
}

void render_minigame1(void) {
    al_clear_to_color(al_map_rgb(50, 50, 70)); // Dark blue-grey background

    float plant_base_y = SCREEN_HEIGHT * 0.65f; // Adjusted for more space for flower
    float plant_x = SCREEN_WIDTH / 2.0f;
    float stem_height = 20 + flower_plant.growth_stage * 15; // Increased growth factor

    // Draw Plant
    if (!seed_planted) {
        al_draw_text(font, al_map_rgb(255, 255, 255), plant_x, plant_base_y - 50, ALLEGRO_ALIGN_CENTER, "請先種下種子");
    } else {
        // Stage 0 (Seed)
        if (flower_plant.growth_stage == 0) {
            al_draw_filled_circle(plant_x, plant_base_y, 10, al_map_rgb(139, 69, 19)); // Brown
        } else { // Stages 1-8 (Growing stem and flower)
            // Stem (common to all growth stages > 0)
            al_draw_filled_rectangle(plant_x - 4, plant_base_y - stem_height, plant_x + 4, plant_base_y, al_map_rgb(0, 128, 0)); // Green stem

            // Leaves (example, can be more elaborate)
            if (flower_plant.growth_stage >= 2) { // First leaf
                 al_draw_filled_triangle(plant_x + 4, plant_base_y - stem_height * 0.3f,
                                        plant_x + 4, plant_base_y - stem_height * 0.3f - 15,
                                        plant_x + 4 + 25, plant_base_y - stem_height * 0.3f - 7,
                                        al_map_rgb(34, 139, 34)); // Forest Green
            }
            if (flower_plant.growth_stage >= 3) { // Second leaf (opposite side)
                 al_draw_filled_triangle(plant_x - 4, plant_base_y - stem_height * 0.5f,
                                        plant_x - 4, plant_base_y - stem_height * 0.5f - 15,
                                        plant_x - 4 - 25, plant_base_y - stem_height * 0.5f - 7,
                                        al_map_rgb(34, 139, 34));
            }
             if (flower_plant.growth_stage >= 4) { 
                 al_draw_filled_triangle(plant_x + 4, plant_base_y - stem_height * 0.7f,
                                        plant_x + 4, plant_base_y - stem_height * 0.7f - 15,
                                        plant_x + 4 + 20, plant_base_y - stem_height * 0.7f - 7,
                                        al_map_rgb(34, 139, 34)); 
            }


            // Stage 8 (Flower)
            if (flower_plant.growth_stage >= songs_to_flower) {
                // Petals
                for (int i = 0; i < 6; ++i) {
                    float angle = (ALLEGRO_PI * 2.0f / 6.0f) * i;
                    al_draw_filled_circle(plant_x + cos(angle) * 20,
                                          (plant_base_y - stem_height - 25) + sin(angle) * 20,
                                          12, al_map_rgb(255, 105, 180)); // Pink petals
                }
                // Flower Center
                al_draw_filled_circle(plant_x, plant_base_y - stem_height - 25, 18, al_map_rgb(255, 255, 0)); // Yellow center
                al_draw_text(font, al_map_rgb(255, 215, 0), plant_x, plant_base_y - stem_height - 70, ALLEGRO_ALIGN_CENTER, "開花了!");
            }
        }
    }
    
    // Display "請唱歌" message if needed
    if (displayPleaseSingMessage) {
        al_draw_text(font, al_map_rgb(255, 100, 100), SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50, ALLEGRO_ALIGN_CENTER, "請唱歌 (至少30秒且夠大聲)");
        // For debugging:
        // al_draw_textf(font, al_map_rgb(200, 200, 200), SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 80, ALLEGRO_ALIGN_CENTER, "錄音長度: %.2f s", audioLengthSeconds);
        // al_draw_textf(font, al_map_rgb(200, 200, 200), SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 110, ALLEGRO_ALIGN_CENTER, "聲音合格: %s", decibelsOkay ? "是" : "否");
    }


    // Draw Buttons (conditionally)
    // Plant Seed button
    if (!seed_planted) {
        Button* b = &minigame_buttons[0];
        al_draw_filled_rectangle(b->x, b->y, b->x + b->width, b->y + b->height, b->is_hovered ? b->hover_color : b->color);
        al_draw_text(font, b->text_color, b->x + b->width / 2, b->y + (b->height / 2) - (al_get_font_line_height(font) / 2), ALLEGRO_ALIGN_CENTER, b->text);
    }
    // Start Singing button (show if not fully grown and not singing)
    if (seed_planted && !is_singing && flower_plant.growth_stage < songs_to_flower) {
        Button* b = &minigame_buttons[1];
        al_draw_filled_rectangle(b->x, b->y, b->x + b->width, b->y + b->height, b->is_hovered ? b->hover_color : b->color);
        al_draw_text(font, b->text_color, b->x + b->width / 2, b->y + (b->height / 2) - (al_get_font_line_height(font) / 2), ALLEGRO_ALIGN_CENTER, b->text);
    }
    // Harvest button (show if fully grown and not singing)
    else if (seed_planted && !is_singing && flower_plant.growth_stage >= songs_to_flower) {
        Button* b = &minigame_buttons[5];
        al_draw_filled_rectangle(b->x, b->y, b->x + b->width, b->y + b->height, b->is_hovered ? b->hover_color : b->color);
        al_draw_text(font, b->text_color, b->x + b->width / 2, b->y + (b->height / 2) - (al_get_font_line_height(font) / 2), ALLEGRO_ALIGN_CENTER, b->text);
    }
    // Restart and Finish Singing buttons (shown together when singing)
    if (is_singing) {
        Button* b_restart = &minigame_buttons[2];
        al_draw_filled_rectangle(b_restart->x, b_restart->y, b_restart->x + b_restart->width, b_restart->y + b_restart->height, b_restart->is_hovered ? b_restart->hover_color : b_restart->color);
        al_draw_text(font, b_restart->text_color, b_restart->x + b_restart->width / 2, b_restart->y + (b_restart->height / 2) - (al_get_font_line_height(font) / 2), ALLEGRO_ALIGN_CENTER, b_restart->text);

        Button* b_finish = &minigame_buttons[3];
        al_draw_filled_rectangle(b_finish->x, b_finish->y, b_finish->x + b_finish->width, b_finish->y + b_finish->height, b_finish->is_hovered ? b_finish->hover_color : b_finish->color);
        al_draw_text(font, b_finish->text_color, b_finish->x + b_finish->width / 2, b_finish->y + (b_finish->height / 2) - (al_get_font_line_height(font) / 2), ALLEGRO_ALIGN_CENTER, b_finish->text);
    }
    // Exit Minigame button (always visible)
    Button* b_exit = &minigame_buttons[4];
    al_draw_filled_rectangle(b_exit->x, b_exit->y, b_exit->x + b_exit->width, b_exit->y + b_exit->height, b_exit->is_hovered ? b_exit->hover_color : b_exit->color);
    al_draw_text(font, b_exit->text_color, b_exit->x + b_exit->width / 2, b_exit->y + (b_exit->height / 2) - (al_get_font_line_height(font) / 2), ALLEGRO_ALIGN_CENTER, b_exit->text);


    // Draw Text Info
    al_draw_text(font, al_map_rgb(220, 220, 255), SCREEN_WIDTH / 2, 30, ALLEGRO_ALIGN_CENTER, "唱歌種花小遊戲");
    if (seed_planted) {
        al_draw_textf(font, al_map_rgb(200, 200, 200), SCREEN_WIDTH - 150, 30, ALLEGRO_ALIGN_RIGHT, "已唱歌曲: %d / %d", flower_plant.songs_sung, songs_to_flower);
    }
}

void handle_minigame1_input(ALLEGRO_EVENT ev) {
    // Mouse movement for hover effects
    if (ev.type == ALLEGRO_EVENT_MOUSE_AXES) {
        // Reset hover states for all buttons first, only on mouse movement
        for (int i = 0; i < NUM_MINIGAME1_BUTTONS; ++i) {
            minigame_buttons[i].is_hovered = false;
        }

        // Plant Seed
        if (!seed_planted && ev.mouse.x >= minigame_buttons[0].x && ev.mouse.x <= minigame_buttons[0].x + minigame_buttons[0].width &&
            ev.mouse.y >= minigame_buttons[0].y && ev.mouse.y <= minigame_buttons[0].y + minigame_buttons[0].height) {
            minigame_buttons[0].is_hovered = true;
        }
        // Start Singing
        else if (seed_planted && !is_singing && flower_plant.growth_stage < songs_to_flower &&
                 ev.mouse.x >= minigame_buttons[1].x && ev.mouse.x <= minigame_buttons[1].x + minigame_buttons[1].width &&
                 ev.mouse.y >= minigame_buttons[1].y && ev.mouse.y <= minigame_buttons[1].y + minigame_buttons[1].height) {
            minigame_buttons[1].is_hovered = true;
        }
        // Harvest button
        else if (seed_planted && !is_singing && flower_plant.growth_stage >= songs_to_flower &&
                 ev.mouse.x >= minigame_buttons[5].x && ev.mouse.x <= minigame_buttons[5].x + minigame_buttons[5].width &&
                 ev.mouse.y >= minigame_buttons[5].y && ev.mouse.y <= minigame_buttons[5].y + minigame_buttons[5].height) {
            minigame_buttons[5].is_hovered = true;
        }
        // Restart and Finish Singing (when is_singing is true)
        else if (is_singing) {
            if (ev.mouse.x >= minigame_buttons[2].x && ev.mouse.x <= minigame_buttons[2].x + minigame_buttons[2].width &&
                ev.mouse.y >= minigame_buttons[2].y && ev.mouse.y <= minigame_buttons[2].y + minigame_buttons[2].height) {
                minigame_buttons[2].is_hovered = true;
            }
            if (ev.mouse.x >= minigame_buttons[3].x && ev.mouse.x <= minigame_buttons[3].x + minigame_buttons[3].width &&
                ev.mouse.y >= minigame_buttons[3].y && ev.mouse.y <= minigame_buttons[3].y + minigame_buttons[3].height) {
                minigame_buttons[3].is_hovered = true;
            }
        }
        // Exit button (always check)
        if (ev.mouse.x >= minigame_buttons[4].x && ev.mouse.x <= minigame_buttons[4].x + minigame_buttons[4].width &&
            ev.mouse.y >= minigame_buttons[4].y && ev.mouse.y <= minigame_buttons[4].y + minigame_buttons[4].height) {
            minigame_buttons[4].is_hovered = true;
        }
    }
    // Mouse button click
    else if (ev.type == ALLEGRO_EVENT_MOUSE_BUTTON_DOWN) {
        if (ev.mouse.button == 1) { // Left mouse button
            bool button_clicked = false;
            // Plant Seed
            if (!seed_planted && minigame_buttons[0].is_hovered) {
                seed_planted = true;
                is_singing = false; // Reset singing state
                flower_plant.songs_sung = 0; // Reset progress if re-planting
                flower_plant.growth_stage = 0;
                button_clicked = true;
            }
            // Start Singing
            else if (seed_planted && !is_singing && flower_plant.growth_stage < songs_to_flower && minigame_buttons[1].is_hovered) {
                is_singing = true;
                // start_actual_audio_recording() is called below, no need for is_singing = true; twice
                start_actual_audio_recording();
                printf("Minigame: Start Singing button clicked. Actual audio recording should start.\n");
                button_clicked = true;
            }
            // Restart or Finish Singing
            else if (is_singing) {
                if (minigame_buttons[2].is_hovered) { // Restart
#ifdef _WIN32
                    if (hWaveIn) { // Ensure device is open before trying to stop/unprepare
                        waveInStop(hWaveIn);
                        MMRESULT resetResult = waveInReset(hWaveIn);
                        if (resetResult != MMSYSERR_NOERROR) {
                            fprintf(stderr, "waveInReset failed with error %d\n", resetResult);
                        }
                        if (waveHdr.dwFlags & WHDR_PREPARED) {
                           MMRESULT unprepareResult = waveInUnprepareHeader(hWaveIn, &waveHdr, sizeof(WAVEHDR));
                           if (unprepareResult != MMSYSERR_NOERROR) {
                               fprintf(stderr, "waveInUnprepareHeader failed in restart: %d\n", unprepareResult);
                           }
                        }
                    }
#else
                    // For non-Windows, stopping and starting is simulated by just calling start again
                    // which resets timers and flags.
                    printf("DEBUG: Non-Windows Restart: Simulating stop and restart.\n");
#endif
                    start_actual_audio_recording(); // This will re-prepare and start (or simulate for non-Win)
                    printf("Minigame: Restart singing button clicked. Audio recording restarted.\n");
                    button_clicked = true;
                }
                else if (minigame_buttons[3].is_hovered) { // Finish Singing
                    is_singing = false;
                    bool sound_was_valid = stop_actual_audio_recording();

                    printf("Minigame: Finish Singing button clicked. Audio recording stopped.\n"); 
                       
                    if (sound_was_valid) {
                        if (flower_plant.songs_sung < songs_to_flower) {
                            flower_plant.songs_sung++;
                        }
                        flower_plant.growth_stage = flower_plant.songs_sung; 
                        if (flower_plant.growth_stage > songs_to_flower) {
                            flower_plant.growth_stage = songs_to_flower;
                        }
                        printf("DEBUG: Valid song recorded, growth updated.\n");
                    } else {
                        printf("DEBUG: Invalid sound detected (too short or too quiet). Song not counted.\n");
                        // displayPleaseSingMessage should be true if stop_actual_audio_recording returned false
                    }
                    button_clicked = true;
                }
            }
            // Harvest button
            else if (seed_planted && !is_singing && flower_plant.growth_stage >= songs_to_flower && minigame_buttons[5].is_hovered) {
                if (rand() % 2 == 0) { // 50% chance for a devil flower
                    player.item_quantities[1]++;
                    printf("DEBUG: Harvested a Devil Flower! Total: %d\n", player.item_quantities[1]);
                } else {
                    player.item_quantities[0]++;
                    printf("DEBUG: Harvested a regular Flower. Total: %d\n", player.item_quantities[0]);
                }

                flower_plant.songs_sung = 0;
                flower_plant.growth_stage = 0;
                seed_planted = false; 
                is_singing = false;
                // No need to call init_minigame1 here, just reset state for replanting
                button_clicked = true;
            }
            // Exit button
            if (minigame_buttons[4].is_hovered) { 
                cleanup_audio_recording(); // Clean up audio resources before exiting
                game_phase = GROWTH; 
                // init_minigame1(); // No, this will be called when entering minigame again.
                                         // cleanup is important here.
                button_clicked = true; 
            }

            if (button_clicked) {
                for (int i = 0; i < NUM_MINIGAME1_BUTTONS; ++i) {
                    minigame_buttons[i].is_hovered = false; // Reset hover on click
                }
            }
        }
    }
    // Key press
    else if (ev.type == ALLEGRO_EVENT_KEY_DOWN) {
        if (ev.keyboard.keycode == ALLEGRO_KEY_ESCAPE) {
            game_phase = GROWTH;
            init_minigame1(); // Reset for next time
        }
    }
}

void update_minigame1(void) {
    // Currently no continuous updates needed for this minigame logic
    // (e.g., animations, timers that run without player input)
}

// --- Audio Recording Functions Implementation ---

static void prepare_audio_recording(void) {
    if (pWaveBuffer == NULL) {
        pWaveBuffer = (char*)malloc(AUDIO_BUFFER_SIZE);
        if (pWaveBuffer == NULL) {
            fprintf(stderr, "Failed to allocate audio buffer.\n");
            return; 
        }
    }

    WAVEFORMATEX wfx;
    wfx.wFormatTag = WAVE_FORMAT_PCM;
    wfx.nChannels = AUDIO_CHANNELS;
    wfx.nSamplesPerSec = AUDIO_SAMPLE_RATE;
    wfx.nAvgBytesPerSec = AUDIO_SAMPLE_RATE * AUDIO_CHANNELS * (AUDIO_BITS_PER_SAMPLE / 8);
    wfx.nBlockAlign = AUDIO_CHANNELS * (AUDIO_BITS_PER_SAMPLE / 8);
    wfx.wBitsPerSample = AUDIO_BITS_PER_SAMPLE;
    wfx.cbSize = 0;

    MMRESULT result = waveInOpen(&hWaveIn, WAVE_MAPPER, &wfx, 0, 0, CALLBACK_NULL);
    if (result != MMSYSERR_NOERROR) {
        fprintf(stderr, "waveInOpen failed with error %d\n", result);
        if (pWaveBuffer) {
            free(pWaveBuffer);
            pWaveBuffer = NULL;
        }
        hWaveIn = NULL; 
        return;
    }
    printf("DEBUG: Windows Audio recording prepared. Device opened.\n");
}

static void start_actual_audio_recording(void) {
    if (hWaveIn == NULL) {
        prepare_audio_recording(); 
        if (hWaveIn == NULL) {
             fprintf(stderr, "Audio device not available, cannot start recording.\n");
            return;
        }
    }
    
    if (waveHdr.dwFlags & WHDR_PREPARED) {
        waveInUnprepareHeader(hWaveIn, &waveHdr, sizeof(WAVEHDR));
    }
    
    ZeroMemory(&waveHdr, sizeof(WAVEHDR));
    waveHdr.lpData = pWaveBuffer;
    waveHdr.dwBufferLength = AUDIO_BUFFER_SIZE;
    waveHdr.dwFlags = 0;

    if (pWaveBuffer == NULL) return;
    ZeroMemory(pWaveBuffer, AUDIO_BUFFER_SIZE);

    if (waveInPrepareHeader(hWaveIn, &waveHdr, sizeof(WAVEHDR)) != MMSYSERR_NOERROR) {
        fprintf(stderr, "waveInPrepareHeader failed.\n"); return;
    }
    if (waveInAddBuffer(hWaveIn, &waveHdr, sizeof(WAVEHDR)) != MMSYSERR_NOERROR) {
        fprintf(stderr, "waveInAddBuffer failed.\n"); waveInUnprepareHeader(hWaveIn, &waveHdr, sizeof(WAVEHDR)); return;
    }
    if (waveInStart(hWaveIn) != MMSYSERR_NOERROR) {
        fprintf(stderr, "waveInStart failed.\n"); waveInUnprepareHeader(hWaveIn, &waveHdr, sizeof(WAVEHDR)); return;
    }

    isActuallyRecording = true;
    recordingStartTime = timeGetTime();
    displayPleaseSingMessage = false;
    audioLengthSeconds = 0.0f;
    decibelsOkay = false;
    printf("DEBUG: Windows Actual audio recording started.\n");
}

static bool stop_actual_audio_recording(void) {
    if (!isActuallyRecording || hWaveIn == NULL) {
        isActuallyRecording = false; 
        return false;
    }

    DWORD recordingStopTime = timeGetTime();
    waveInReset(hWaveIn); 
    isActuallyRecording = false;

    audioLengthSeconds = (recordingStopTime - recordingStartTime) / 1000.0f;
    printf("DEBUG: Windows Recording stopped. Recorded for %.2f seconds.\n", audioLengthSeconds);

    bool validationSuccess = true;
    if (audioLengthSeconds < 1.0f) { // Real 30s check for Windows
        printf("DEBUG: Windows Recording too short (%.2f s < 30s).\n", audioLengthSeconds);
        displayPleaseSingMessage = true;
        validationSuccess = false;
    } else {
         printf("DEBUG: Windows Recording length OK (%.2f s).\n", audioLengthSeconds);
    }

    short* samples = (short*)pWaveBuffer;
    long max_abs_sample = 0;
    DWORD num_samples_recorded = waveHdr.dwBytesRecorded / (AUDIO_BITS_PER_SAMPLE / 8);

    if (num_samples_recorded == 0 && validationSuccess) {
        printf("DEBUG: Windows No audio data recorded.\n");
        displayPleaseSingMessage = true;
        decibelsOkay = false;
        validationSuccess = false;
    } else if (validationSuccess) { // Only check decibels if length was okay
        for (DWORD i = 0; i < num_samples_recorded; ++i) {
            if (abs(samples[i]) > max_abs_sample) {
                max_abs_sample = abs(samples[i]);
            }
        }
        printf("DEBUG: Windows Max absolute sample value: %ld\n", max_abs_sample);
        if (max_abs_sample < 1) { 
            printf("DEBUG: Windows Recording too quiet (max_abs_sample: %ld < 1000).\n", max_abs_sample);
            displayPleaseSingMessage = true;
            decibelsOkay = false;
            validationSuccess = false;
        } else {
            printf("DEBUG: Windows Recording volume OK.\n");
            decibelsOkay = true;
        }
    }

    if (waveHdr.dwFlags & WHDR_PREPARED) {
        waveInUnprepareHeader(hWaveIn, &waveHdr, sizeof(WAVEHDR));
    }
    
    if (!validationSuccess) printf("DEBUG: Windows Audio validation FAILED.\n");
    else printf("DEBUG: Windows Audio validation SUCCEEDED.\n");
    return validationSuccess;
}

static void cleanup_audio_recording(void) {
    printf("DEBUG: Windows cleanup_audio_recording() called.\n");
    if (isActuallyRecording && hWaveIn != NULL) {
        waveInReset(hWaveIn);
        isActuallyRecording = false;
    }
    if (hWaveIn != NULL) {
        if (waveHdr.dwFlags & WHDR_PREPARED) {
            waveInUnprepareHeader(hWaveIn, &waveHdr, sizeof(WAVEHDR));
        }
        waveInClose(hWaveIn);
        hWaveIn = NULL;
    }
    if (pWaveBuffer != NULL) {
        free(pWaveBuffer);
        pWaveBuffer = NULL;
    }
}
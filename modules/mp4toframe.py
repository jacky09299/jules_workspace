import cv2
import os

video_path = "start.mp4"
output_dir = "frames"
fps_target = 30

os.makedirs(output_dir, exist_ok=True)

cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)
frame_interval = int(round(fps / fps_target))

frame_count = 0
saved_count = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break
    if frame_count % frame_interval == 0:
        filename = os.path.join(output_dir, f"frame_{saved_count:03d}.png")
        cv2.imwrite(filename, frame)
        saved_count += 1
    frame_count += 1

cap.release()
print(f"已儲存 {saved_count} 張圖片在 {output_dir}/")

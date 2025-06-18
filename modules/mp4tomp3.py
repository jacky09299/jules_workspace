import os
from moviepy import VideoFileClip

# 設定來源資料夾與輸出資料夾
input_folder = "mp4_folder"       # 放 MP4 的資料夾
output_folder = "mp3_output"      # 轉換後 MP3 的資料夾

# 若輸出資料夾不存在，則建立它
os.makedirs(output_folder, exist_ok=True)

# 遍歷資料夾內所有 MP4 檔案
for filename in os.listdir(input_folder):
    if filename.lower().endswith(".mp4"):
        mp4_path = os.path.join(input_folder, filename)
        mp3_filename = os.path.splitext(filename)[0] + ".mp3"
        mp3_path = os.path.join(output_folder, mp3_filename)

        print(f"正在處理：{filename}")
        try:
            video = VideoFileClip(mp4_path)
            audio = video.audio
            audio.write_audiofile(mp3_path)
            audio.close()
            video.close()
            print(f"已儲存：{mp3_path}")
        except Exception as e:
            print(f"錯誤：{filename} 無法轉換，原因：{e}")
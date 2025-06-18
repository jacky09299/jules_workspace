import os
from moviepy.editor import VideoFileClip

# 設定來源資料夾與輸出資料夾
input_folder = "mp4_folder"       # 放 MP4 的資料夾
output_folder = "ogg_output"      # 轉換後 OGG 的資料夾

# 若輸出資料夾不存在，則建立它
os.makedirs(output_folder, exist_ok=True)

# 遍歷資料夾內所有 MP4 檔案
for filename in os.listdir(input_folder):
    if filename.lower().endswith(".mp4"):
        mp4_path = os.path.join(input_folder, filename)
        # 將副檔名改為 .ogg
        ogg_filename = os.path.splitext(filename)[0] + ".ogg"
        ogg_path = os.path.join(output_folder, ogg_filename)

        print(f"正在處理：{filename}")
        try:
            # 讀取影片檔
            video = VideoFileClip(mp4_path)
            # 取得音訊
            audio = video.audio
            # 寫入 OGG 檔案，並指定 codec 為 'libvorbis'
            audio.write_audiofile(ogg_path, codec='libvorbis')
            # 關閉檔案以釋放資源
            audio.close()
            video.close()
            print(f"已儲存：{ogg_path}")
        except Exception as e:
            print(f"錯誤：{filename} 無法轉換，原因：{e}")

print("所有檔案處理完畢！")
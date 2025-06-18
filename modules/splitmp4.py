from moviepy.editor import VideoFileClip

def split_video(input_path, output_path1, output_path2):
    video = VideoFileClip(input_path)
    duration = video.duration
    mid_point = duration / 2

    # 切成前半段與後半段
    first_half = video.subclip(0, mid_point)
    second_half = video.subclip(mid_point, duration)

    # 儲存影片
    first_half.write_videofile(output_path1, codec="libx264", audio_codec="aac")
    second_half.write_videofile(output_path2, codec="libx264", audio_codec="aac")

# 🔧 修改這些路徑為你自己的檔案
input_file = "start.mp4"
output_file1 = "start_part1.mp4"
output_file2 = "start_part2.mp4"

split_video(input_file, output_file1, output_file2)

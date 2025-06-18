import os
from PyPDF2 import PdfReader, PdfWriter

def split_pdf_by_page_ranges(input_pdf, page_ranges, output_pattern=None):
    """
    根據指定的頁碼範圍分割PDF
    
    參數:
    input_pdf (str): 輸入PDF檔案路徑
    page_ranges (list): 頁碼範圍列表，每個元素為(起始頁,結束頁)的元組
    output_pattern (str): 輸出檔案命名模式
    """
    # 預設輸出模式
    if output_pattern is None:
        filename = os.path.basename(input_pdf)
        basename = os.path.splitext(filename)[0]
        output_pattern = f"Chapter{{i}}_{basename}.pdf"
    
    # 讀取PDF
    try:
        reader = PdfReader(input_pdf)
        total_pages = len(reader.pages)
        print(f"PDF總頁數: {total_pages}")
        
        # 創建輸出資料夾
        output_dir = "split_chapters"
        os.makedirs(output_dir, exist_ok=True)
        
        # 分割PDF
        for i, (start_page, end_page) in enumerate(page_ranges):
            # 檢查頁碼範圍
            if start_page < 0:
                start_page = 0
            if end_page >= total_pages:
                end_page = total_pages - 1
            
            # 創建新的PDF
            writer = PdfWriter()
            
            # 添加頁面
            for page_num in range(start_page, end_page + 1):
                writer.add_page(reader.pages[page_num])
            
            # 使用提供的模式命名輸出文件
            chapter_num = i + 1
            output_filename = output_pattern.format(i=chapter_num, filename=os.path.basename(input_pdf))
            output_path = os.path.join(output_dir, output_filename)
            
            # 寫入新PDF
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            
            print(f"已創建單元 {chapter_num}: {output_path} (頁碼範圍: {start_page+1}-{end_page+1})")
        
        print(f"完成! 所有單元已分割到 {output_dir} 資料夾")
        
    except Exception as e:
        print(f"處理PDF時發生錯誤: {e}")

if __name__ == "__main__":
    # 您的PDF檔案路徑
    input_pdf = "VANDER_S_HUMAN_PHYSIOLOGY_2023.pdf"
    
    # 定義輸出檔案名稱模式
    output_pattern = "Chapter{i}_VANDER_S_HUMAN_PHYSIOLOGY_2023.pdf"
    
    # 您提供的頁碼 (注意: PDF頁碼從0開始，所以要減去1)
    chapter_start_pages = [60,102,152,250,300,337,445,530,580,664,703,788,953,1046,1138,1216,1276,1387,1464,1497]
    
    # 將頁碼轉換為0開始的索引
    zero_based_pages = [page-1 for page in chapter_start_pages]
    
    # 創建頁碼範圍，只取1-9章
    page_ranges = []
    for i in range(len(zero_based_pages) - 1):
        if i < 19:  # 只取前9章
            page_ranges.append((zero_based_pages[i], zero_based_pages[i+1] - 1))
    
    print("將分割以下頁碼範圍:")
    for i, (start, end) in enumerate(page_ranges):
        print(f"單元 {i+1}: 頁碼 {start+1} 到 {end+1}")
    
    # 分割PDF
    split_pdf_by_page_ranges(input_pdf, page_ranges, output_pattern)
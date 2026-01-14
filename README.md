# 模組化演算法面板 (Modular Algorithm Panel)

這是一個基於 Python Tkinter 的模組化節點編輯器，允許使用者通過拖拉方塊來設計和執行演算法流程。

## 功能特色
- **視覺化編輯**: 拖拉節點、連線、分支。
- **內建演算法**: A* 路徑搜尋、圖像二值化、路徑疊圖。
- **擴充性**: 支援自訂 Python 腳本節點。
- **專案管理**: 支援 JSON 格式的專案儲存與載入。

## 安裝需求

請確保您已安裝 Python 3.10 以上版本。

安裝依賴套件：
```bash
pip install -r requirements.txt
```

## 執行方式

在專案根目錄下執行：

```bash
# Linux / macOS
export PYTHONPATH=$PYTHONPATH:.
python src/main.py

# Windows (PowerShell)
$env:PYTHONPATH="."
python src/main.py
```

## 快速上手

1. 啟動程式。
2. 點擊選單 `檔案` -> `開啟專案`。
3. 選擇 `example_project.json`。
4. 點擊選單 `執行` -> `執行`。
5. 查看生成的 `result_map.png` 和 `path_result.txt`。

## 模組說明

- **InputImageNode**: 讀取圖片檔案。
- **ImageToGridNode**: 將圖片轉換為二維網格 (障礙物=1, 可通行=0)。
- **AStarNode**: 執行 A* 演算法計算最短路徑。
- **PathOverlayNode**: 將計算出的路徑繪製回原圖。
- **SaveNode**: 儲存資料 (文字、JSON 或圖片)。
- **CustomScriptNode**: 執行自訂 Python 程式碼片段。

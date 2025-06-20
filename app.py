import subprocess
import os

# 構造要執行的 bat 命令
command = (
    f'call "{os.environ["USERPROFILE"]}\\anaconda3\\Scripts\\activate.bat" tools && '
    'python main.py'
)

# 用 cmd /k /c 執行整段
subprocess.run(["cmd.exe", "/c", command], shell=True)

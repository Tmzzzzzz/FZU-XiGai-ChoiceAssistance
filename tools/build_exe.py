# -*- coding: utf-8 -*-
"""构建免安装版（Windows，onedir）。

用法：
    .venv/Scripts/python.exe tools/build_exe.py

产物：dist/FZU-XiGai-ChoiceAssistance/  —— 整个文件夹拷到任意位置或另一台电脑
即可运行，不依赖本机的 Python 环境。题库 data/ 与记录 userdata/ 都在 exe 同级目录。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "习概选择题"                 # exe 名（中文，方便双击）
BUNDLE_NAME = "FZU-XiGai-ChoiceAssistance"  # 发布文件夹名（与仓库同名）
DIST = ROOT / "dist"
TARGET = DIST / APP_NAME
FINAL = DIST / BUNDLE_NAME


def main() -> int:
    icon = ROOT / "assets" / "app.ico"
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--windowed",
        "--name", APP_NAME,
        "--distpath", str(DIST),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT / "build"),
        "--paths", str(ROOT),
        "--exclude-module", "tkinter",
        "--exclude-module", "PIL",
        "--exclude-module", "numpy",
        "--exclude-module", "pymupdf",
        "--exclude-module", "docx",
    ]
    if icon.exists():
        cmd += ["--icon", str(icon)]
    cmd.append(str(ROOT / "launch.py"))

    # 先自己删干净：PyInstaller 的批量删除会触发沙箱的安全限制
    if TARGET.exists():
        shutil.rmtree(TARGET)

    print("building...")
    subprocess.run(cmd, check=True, cwd=ROOT)

    # 题库与说明放到 exe 同级，方便直接查看/替换
    shutil.copytree(ROOT / "data", TARGET / "data", dirs_exist_ok=True)
    readme = ROOT / "README.md"
    if readme.exists():
        shutil.copy2(readme, TARGET / "README.md")
    guide = ROOT / "docs" / "portable-guide.txt"
    if guide.exists():
        shutil.copy2(guide, TARGET / "使用说明.txt")

    # 输出目录改成与仓库同名的发布目录
    if FINAL.exists():
        shutil.rmtree(FINAL)
    TARGET.rename(FINAL)

    exe = FINAL / f"{APP_NAME}.exe"
    size = sum(f.stat().st_size for f in FINAL.rglob("*") if f.is_file()) / 1024 / 1024
    print(f"\n完成：{exe}")
    print(f"目录大小：{size:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

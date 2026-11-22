# -*- coding: utf-8 -*-
"""打包入口：PyInstaller 从这里启动，避免直接以脚本方式运行包内模块。"""
import sys

from app.__main__ import main

if __name__ == "__main__":
    sys.exit(main())

# main.py — 程序入口（entry point）
import sys
import os

# 确保能找到同目录模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import MainApp


def main():
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    main()

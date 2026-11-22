# 习概选择题 · FZU 期末复习刷题程序

> **仅适用于福州大学（FZU）《习近平新时代中国特色社会主义思想概论》课程的期末复习。**
>
> 题库来自课程下发的选择题汇总，共 271 题。其他院校、其他教材版本的考点表述可能不同，请勿直接套用。

PySide6 桌面程序 + 结构化题库：随机练习、按章节 / 知识点 / 题型筛选、只做错题；作答后即时判分并显示解析，自带统计与错题本。

![主界面](docs/screenshots/01-overview.png)

![深色主题](docs/screenshots/06-dark.png)

## 功能

- **三种模式**：随机（优先未做过的题）／筛选（章节 + 知识点 + 题型）／只做错题
- **即时反馈**：正确、错选、漏选分色标记，提交后给出正确答案与解析
- **统计**：已做、正确、错误、正确率环图、题库覆盖率
- **错题本**：答错自动收录、答对自动移出，点击可跳转
- **状态保留**：切换模式、改筛选都不清空统计与错题；进度本地持久化
- **深色模式**：右上角日 / 月按钮切换
- **键盘操作**：`A–E` / `1–5` 选择，`Enter` 提交或下一题，`←` `→` 翻页，`R` 打乱顺序

## 运行

系统要求：Windows 10 / 11（64 位）。

**免安装版**：从 Releases 下载压缩包，解压后双击 `习概选择题.exe`。记录写在同级 `userdata\`。

**源码运行**（Python 3.10+）：

```bat
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m app
```

也可以直接双击 `run.bat`，它会自检并准备环境。

## 题库

271 题 = 176 单选 + 95 多选，覆盖 18 章、100 个知识点。每题包含题干、全部选项、答案、解析与章节 / 知识点分类。

- 题库文件：`data/questions.json`

## 目录

```
app/      程序（UI 与业务逻辑分离）
data/     结构化题库
tools/    从 PDF/DOCX 重建题库、生成图标、打包 exe
tests/    端到端自测
docs/     数据报告、截图、便携版说明
```

## 打包与迁移

`.venv\Scripts\python tools\build_exe.py` 生成 `dist/习概选择题/`（约 98 MB，自包含 Qt 运行时）。
使用说明、换机与备份方式见 [docs/portable-guide.txt](docs/portable-guide.txt)。

## 说明

- 做题记录保存在 `userdata/progress.json`，删除该文件即清空进度。
- 题库内容仅供课程复习使用。

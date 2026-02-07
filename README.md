# Dwarf Fortress Wiki OCR Tool

矮人要塞 Wiki OCR 识别工具 - 帮助中文玩家快速识别游戏中的英文文本并查阅 Wiki 词条。

## 功能介绍

- **截图识别**: 截取屏幕区域，自动识别英文文字
- **Wiki 匹配**: 自动匹配 Dwarf Fortress Wiki 词条
- **英语词典**: 基于 ECDICT 的英汉词典支持（150万+词汇，可选）
- **双语显示**: 支持中英文切换显示
- **离线访问**: 本地 Wiki 数据库，无需联网即可查阅
- **图片支持**: 异步加载 Wiki 中的图片
- **链接导航**: 点击 Wiki 内链可跳转到相关词条

## 项目结构

```
df-ocr/
├── run.bat                      # Windows 启动脚本
├── requirements.txt             # Python 依赖
├── translation_map.json         # 翻译映射表
├── src/                         # 源代码
│   ├── ocr_tool.py             # 主程序入口
│   └── wiki_to_html.py         # Wiki 格式转 HTML
├── scripts/                     # 工具脚本
│   ├── split_wiki.py           # Wiki XML 分割工具
│   ├── build_translation_map.py # 构建翻译映射表
│   └── translate_large_files.py # 大文件翻译工具
├── tests/                       # 单元测试
│   ├── test_wiki_to_html.py    # Wiki 转 HTML 测试
│   └── test_translation.py     # 翻译功能测试
├── wiki/                        # 英文 Wiki 词条 (~5136 文件)
├── wiki_cn/                     # 中文翻译词条 (~838 文件)
└── Tesseract-OCR/               # OCR 引擎
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

依赖包：
- PyQt5 >= 5.15.0
- pytesseract >= 0.3.10
- Pillow >= 9.0.0

### 2. 下载英语词典（可选）

如果需要英汉词典功能，可以下载 ECDICT 数据库：

```bash
python scripts/download_ecdict.py
```

这将下载约 450MB 的词典数据库到项目根目录。**如果跳过此步骤，程序仍可正常使用 Wiki 查询功能。**

**词典功能包括：**
- 150万+ 英语词汇
- 音标、释义、词源等详细信息
- 自动词形还原（running → run）
- 模糊搜索支持

### 3. 启动程序

**方式一：双击启动**
```
双击 run.bat
```

**方式二：命令行启动**
```bash
python src/ocr_tool.py
```

### 4. 使用方法

1. 点击「截图并识别词条」按钮
2. 拖动鼠标选择要识别的屏幕区域
3. 程序自动识别英文文字并显示匹配的结果：
   - 📖 Wiki 词条（绿色按钮）
   - 📚 词典释义（蓝色按钮，需下载词典）
4. 点击「中/EN」按钮切换中英文显示
5. 点击 Wiki 链接可跳转到相关词条

## 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Esc` | 取消截图 |

## 翻译系统

采用三层翻译策略：

1. **人工翻译层**（最高优先级）
   - `wiki_cn/` 目录下的完整翻译文件
   
2. **标题映射层**
   - 词条名称的中英文对照
   
3. **词汇替换层**（兜底）
   - 基于词汇表的自动替换
   - 标记为「⚠️ [临时翻译]」

## 开发相关

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行单个测试文件
python tests/test_wiki_to_html.py -v
python tests/test_translation.py -v
```

### 构建翻译映射表

```bash
python scripts/build_translation_map.py
```

### 分割 Wiki XML

```bash
python scripts/split_wiki.py Dwarf+Fortress+Wiki-20260206192244.xml wiki
```

## 数据来源

- **英文 Wiki**: [Dwarf Fortress Wiki](https://dwarffortresswiki.org/)
- **中文翻译**: 社区贡献（目前约 16% 词条有中文翻译）
- **英语词典**: [ECDICT](https://github.com/skywind3000/ECDICT) - 开源英汉词典数据库（150万+词汇）

## 许可证

本项目仅供学习和个人使用。

## 致谢

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - 开源 OCR 引擎
- [Dwarf Fortress Wiki](https://dwarffortresswiki.org/) - 词条数据来源
- [ECDICT](https://github.com/skywind3000/ECDICT) - 开源英汉词典数据库

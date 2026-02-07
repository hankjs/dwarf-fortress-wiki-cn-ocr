# 句子翻译功能使用指南

## 功能说明

**句子翻译**功能使用 MyMemory API 将 OCR 识别的英文句子实时翻译成中文。

### 特点

- ✅ **在线翻译** - MyMemory API，翻译质量好
- ✅ **免费额度** - 500次/天（免费），1000次/天（注册后）
- ✅ **术语保护** - 1579个游戏术语自动替换为标准译名
- ✅ **异步执行** - 后台翻译，UI 不卡顿
- ✅ **智能触发** - 仅对多单词文本启用

---

## 快速开始

### 1. 安装依赖

```bash
pip install requests
```

### 2. 启动应用

```bash
python src/ocr_tool.py
```

**无需额外配置**，有网络即可使用！

---

## 使用方法

### OCR 翻译

1. 点击"截图"按钮
2. 框选包含多个单词的英文文本
3. 等待 1-3 秒，翻译自动完成
4. 点击"🈯 翻译"查看结果

### 搜索翻译

1. 在搜索框输入多个单词（如 "dwarf miner"）
2. 按回车或点击搜索
3. 翻译结果自动出现在列表顶部

---

## 翻译示例

**输入**：
```
The dwarf miner strikes the adamantine vein!
```

**输出**：
```
矮人矿工打击精金矿脉！
```

**术语保护**：
- `dwarf` → `矮人` ✅
- `miner` → `矿工` ✅
- `adamantine` → `精金` ✅
- `vein` → `矿脉` ✅

---

## UI 布局

```
┌─────────────────────────────────────────┐
│  [截图] [搜索框]        [置顶] [CN/EN]  │
├────────────┬────────────────────────────┤
│            │                            │
│  🈯 翻译   │   原文：The dwarf...       │
│  └─ 矮人... │   译文：矮人矿工...        │
│            │                            │
│  📚 字典   │   💡 翻译由 MyMemory 提供  │
│  ├─ word1  │                            │
│  └─ word2  │                            │
│            │                            │
│  📖 Wiki   │                            │
│  └─ Entry1 │                            │
└────────────┴────────────────────────────┘
```

---

## 术语保护机制

翻译前自动将游戏术语替换为标准中文：

```python
原文: "The dwarf miner strikes the adamantine vein"
     ↓ 预处理（替换术语）
中间: "The 矮人 矿工 strikes the 精金 矿脉"
     ↓ MyMemory API 翻译
结果: "矮人矿工打击精金矿脉"
```

**保护的术语**（部分）：
- Dwarf → 矮人
- Fortress → 要塞
- Adamantine → 精金
- Miner → 矿工
- Strike → 打击
- Vein → 矿脉

共 **1579 个术语**受到保护（来自 `translation_map.json`）。

---

## 性能特点

| 项目 | 说明 |
|------|------|
| **响应时间** | 1-3 秒（取决于网络） |
| **内存占用** | 几乎无额外占用 |
| **磁盘占用** | 无需下载文件 |
| **免费额度** | 500 次/天 |

---

## API 限制

### 免费用户
- **额度**：500 次/天
- **无需注册**
- **适合**：个人日常使用

### 注册用户
- **额度**：1000 次/天
- **注册**：https://mymemory.translated.net/
- **可选**：添加 API Key 提升优先级

---

## 故障排除

### 问题 1: 翻译不显示

**可能原因**：
- ✓ 只识别到单个单词 → 正常，单词用字典
- ✗ 无网络连接 → 检查网络
- ✗ API 额度用完 → 等待明天或注册账号

### 问题 2: 翻译一直显示 "翻译中..."

**解决方案**：
1. 检查终端输出的错误信息
2. 检查网络连接（访问 https://api.mymemory.translated.net/）
3. 检查防火墙设置
4. 重试（重新搜索或 OCR）

### 问题 3: 翻译质量不佳

**建议**：
- 游戏术语应该准确（已保护）
- 复杂句子配合 Wiki 和字典理解
- 专业词汇以字典为准

---

## 高级配置（可选）

### 添加 API Key（提升优先级）

1. 注册账号：https://mymemory.translated.net/
2. 获取 API Key
3. 编辑 `src/sentence_translator.py`：

```python
class SentenceTranslator:
    API_URL = "https://api.mymemory.translated.net/get"
    API_KEY = "your_api_key_here"  # 添加这一行

    def _call_mymemory_api(self, text: str):
        params = {
            'q': text,
            'langpair': 'en|zh-CN',
            'key': self.API_KEY  # 添加这一行
        }
        # ...
```

---

## 常见问题

**Q: 需要付费吗？**
A: 免费用户 500 次/天，注册后 1000 次/天，对个人使用完全够用。

**Q: 离线能用吗？**
A: 翻译需要网络。离线时自动跳过，不影响 Wiki 和字典功能。

**Q: 翻译速度慢？**
A: 取决于网络速度。翻译在后台执行，不会阻塞 UI。

**Q: 术语翻译不对？**
A: 可以修改 `translation_map.json` 中的 `vocabulary_map` 添加自定义术语。

**Q: 如何查看剩余额度？**
A: MyMemory 不提供额度查询 API。免费用户每天 UTC 0:00 重置。

---

## 技术细节

- **API**: MyMemory Translation API
- **官网**: https://mymemory.translated.net/
- **文档**: https://mymemory.translated.net/doc/spec.php
- **翻译方向**: 英语 → 简体中文 (`en|zh-CN`)
- **超时设置**: 10 秒
- **错误处理**: 自动降级（失败时不显示翻译）

---

**问题反馈**: https://github.com/anthropics/claude-code/issues

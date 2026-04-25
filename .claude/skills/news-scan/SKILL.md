---
name: news-scan
description: 拉取并检索宏观/央行/地缘政治新闻。基于 lab/tools/fetch_news.py 的 RSS 采集 + 本地 JSONL 存储。输入时间窗和分类，输出按分类分组的条目（标题/时间/源/URL/摘要）。v0.1 只免费 RSS；v0.2 可加中文源、API 聚合。
---

# news-scan — 新闻扫描技能

## 契约（稳定）

**输入**（自然语言）：
- `since_hours`: 整数，默认 24
- `categories`: 子集或全选，候选 `[central_bank, macro, geopolitics, markets]`
- `keywords`: 可选，按标题+摘要过滤（AND 语义）
- `refresh`: `auto | force | skip`（默认 `auto` — 若今天未拉过则拉）

**输出**（Markdown 结构化）：

```
### 新闻扫描 (since YYYY-MM-DD HH:MM UTC, N items)

#### 🏛️ Central Bank
- [YYYY-MM-DD HH:MM] **<title>** — <source>
  <摘要 ~1 句话>
  <url>
- ...

#### 📈 Macro
- ...

#### 🌍 Geopolitics
- ...

#### 💹 Markets
- ...

### 数据引用
- lab/news/YYYY-MM-DD.jsonl (total: N)
```

## 实现步骤（v0.1）

### 1. 刷新（refresh=auto 且今日文件不存在或 >2h 未更，或 refresh=force）

在仓库根跑：

```bash
python3 lab/tools/fetch_news.py
```

脚本幂等（按 url hash 去重），多跑一次只会追加新条目。

### 2. 读取 + 过滤

```bash
cd /Users/guoqiangzhong/eco_knowladge_base && python3 <<'PY'
import json, datetime, pathlib, sys

since_hours = 24            # 从输入取
categories = None           # None 表示全选；或 ["central_bank", "macro"]
keywords = None             # None 或 ["Fed", "CPI"]

cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=since_hours)
root = pathlib.Path("lab/news")
dates = sorted(root.glob("*.jsonl"))[-3:]  # 最近 3 天足够覆盖 since_hours
items = []
for f in dates:
    for line in f.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        ts = datetime.datetime.fromisoformat(rec["ts"].replace("Z", ""))
        if ts < cutoff:
            continue
        if categories and rec.get("category") not in categories:
            continue
        if keywords:
            blob = (rec.get("title", "") + " " + rec.get("summary", "")).lower()
            if not all(k.lower() in blob for k in keywords):
                continue
        items.append(rec)

# Dedup by url
seen = {}
for r in items:
    seen[r["url"]] = r
items = sorted(seen.values(), key=lambda r: r["ts"], reverse=True)

print(json.dumps({"count": len(items), "items": items}, ensure_ascii=False))
PY
```

### 3. 渲染

- 分组顺序：central_bank → macro → geopolitics → markets（按 emoji 匹配）
- 每组最多 **10 条**（超过则保留最新 10 条并注 "… 其余 N 条省略"）
- 时间转本地时区（Asia/Shanghai）显示
- 摘要 >120 字的截断 + `…`
- 同 title 多源出现时合并（只留最早）

### 4. 空结果处理

如果过去 `since_hours` 小时**没有新闻**：
- 检查是否 `lab/news/` 目录为空 → 提示"首次运行，请 refresh=force"
- 否则说明该时段无新动态；**不要**编造

## 错误场景

- RSS 源 429/500：跳过单源继续，最终报告受影响的 source 列表
- `feedparser` 未安装：报错并建议 `pip3 install feedparser`

## 演进路径

- v0.2：加中文源（财新 / 第一财经 / 华尔街见闻 RSS）
- v0.3：用户订阅关键词，`fetch_news.py` 用 LLM 做每条的 5 秒摘要（可选）
- v0.4：接聚合 API（Serper / NewsAPI），付费源可选

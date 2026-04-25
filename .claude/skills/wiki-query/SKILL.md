---
name: wiki-query
description: 查询知识库，回答经济/金融/投资框架相关问题
trigger: user asks about wiki content or economic concepts
---

# wiki-query — 知识库查询

回答用户问题时，将 wiki 知识作为参考依据。

## 流程

1. **定位相关页面**
   - 读 `knowledge/wiki/index.md` 检索关键词
   - 用 Grep 在 `knowledge/wiki/` 下搜索关键词

2. **读取候选页**
   - 读取匹配的 `.md` 文件
   - 关注 frontmatter 中的 tags、sources、related 信息

3. **综合回答**
   - 引用页面路径和具体内容
   - 突出概念间的关联（内链）
   - 如果答案不在 wiki 中，说明"知识库未覆盖，以下基于通用知识"

## 约束
- 遵循 `knowledge/SCHEMA.md` 的格式规范引用
- 不要编造不存在的 wiki 页
- 涉及数据/数值的内容，优先引用 lab/data/ 的最新值

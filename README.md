# Public Cancer Data Collector

按关键词定期收集公开癌症研究文献，并输出对应数据是否可下载与下载来源。

## 你提出的关键需求（已支持）
- 关键词放在**独立配置文件**中。
- 每组任务包含：`癌种`、`数据类型`、`其他检索关键词`。
- 可以同时存在多组关键词。
- 自动合并同一癌种+数据类型的结果到统一目录（例如 `NSCLC` 与 `Non-Small Cell Lung Cancer` 最终都进入 `outputs/NSCLC/<data_type>/`）。

## 目录组织
- 结果：`outputs/<cancer_type>/<data_type>/papers.csv`
- 状态：`state/<cancer_type>/<data_type>/state.json`

这保证了同一癌种同一数据类型的多组关键词会自动合并并增量更新。

## 配置文件（独立关键词文件）
示例：`configs/keywords.example.json`

核心字段：
- `cancer_type`：标准化癌种名称（用于目录归并，如 `NSCLC`）。
- `data_type`：数据类型（如 `WES`、`RNA`、`scRNA`）。
- `search_aliases`：同义癌种写法（如 `NSCLC` / `Non-Small Cell Lung Cancer`）。
- `extra_keywords`：补充检索词（如 `tumor microenvironment`）。
- `keyword_groups`：可选，手写完整检索表达式；存在时优先使用。

## 运行方式

### 批量按关键词文件运行（推荐）
```bash
python3 collector.py collect-from-keywords --keywords-file ./configs/keywords.example.json
```

### 单次运行（兼容）
```bash
python3 collector.py collect \
  --keyword "(NSCLC) AND (scRNA OR single-cell RNA)" \
  --cancer-type "NSCLC" \
  --data-type "scRNA" \
  --days-back 365 \
  --out ./outputs/NSCLC/scRNA/papers.csv \
  --state ./state/NSCLC/scRNA/state.json
```

## 输出字段
- `paper_id`, `title`, `journal`, `pub_year`, `authors`, `doi`, `source`
- `first_seen_at`, `keyword`, `cancer_type`, `data_type`
- `accession`, `data_type_hint`, `downloadable`, `repository`, `download_url`

## 定时更新（cron）
```bash
0 2 * * * cd /workspace/PublicdataCollect && /usr/bin/python3 collector.py collect-from-keywords --keywords-file ./configs/keywords.json >> ./logs/collector.log 2>&1
```

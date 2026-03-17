# Public Cancer Data Collector

一个用于**按关键词定期收集公开癌症研究文献**并判断其是否包含可下载数据来源的小工具。

## 目标
- 给定关键词（例如 `NSCLC`, `WES`, `RNA-seq`, `scRNA`）检索公开发表文献。
- 从文献信息中提取常见数据集 accession（如 `GSE`, `SRP`, `PRJNA`, `E-MTAB` 等）。
- 输出每篇文献的数据是否可下载、下载入口链接、数据类型线索。
- 通过状态文件实现增量更新，配合 cron 实现定期更新。

## 数据源
- 文献检索：Europe PMC REST API（免费公开）。
- 下载链接规则：基于 accession 前缀映射到对应公开数据库页面。

## 快速开始

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python collector.py collect \
  --keyword "NSCLC scRNA" \
  --days-back 365 \
  --out ./outputs/nsclc_scrna.csv \
  --state ./state/nsclc_scrna_state.json
```

## 命令说明

### 1) collect
执行一次检索并更新状态文件。

```bash
python collector.py collect \
  --keyword "NSCLC WES RNA scRNA" \
  --days-back 365 \
  --out ./outputs/nsclc_all.csv \
  --state ./state/nsclc_all_state.json
```

参数：
- `--keyword`：检索关键词（可包含布尔表达式）。
- `--days-back`：回溯天数。
- `--out`：输出 CSV 文件路径。
- `--state`：状态文件路径（用于增量更新）。
- `--page-size`：每页返回数，默认 100。
- `--max-pages`：最大抓取页数，默认 20。

### 2) collect-from-config
从 JSON 配置读取参数，便于定时任务复用。

```bash
python collector.py collect-from-config --config ./configs/nsclc.json
```

示例配置见 `configs/nsclc.example.json`。

## 输出字段
- `paper_id`：Europe PMC 文献 ID（如 PMID）。
- `title`：标题。
- `journal`：期刊。
- `pub_year`：发表年份。
- `authors`：作者字符串。
- `doi`：DOI。
- `source`：文献来源库。
- `first_seen_at`：首次被本工具记录时间。
- `keyword`：检索关键词。
- `accession`：识别到的数据 accession。
- `data_type_hint`：数据类型线索（WES/RNA/scRNA/ATAC 等）。
- `downloadable`：是否公开可下载（`yes` / `no` / `unknown`）。
- `repository`：推断的数据仓库。
- `download_url`：可访问页面或下载入口。

> 说明：对于 EGA（如 `EGAS...`）这类受控数据会标记为 `no`。

## 定期更新（cron）

每天凌晨 2 点跑一次：

```bash
0 2 * * * cd /workspace/PublicdataCollect && /usr/bin/python3 collector.py collect-from-config --config ./configs/nsclc.json >> ./logs/collector.log 2>&1
```

## 注意事项
- 抽取 accession 依赖文献信息中的显式标注，存在漏检可能。
- 仅依据 accession 前缀推断下载可用性，严格可下载状态仍建议落地时二次校验。
- 如需更强召回，可增加全文抓取与补充规则（例如补充 figshare/Zenodo 链接识别）。

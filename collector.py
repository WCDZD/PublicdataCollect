#!/usr/bin/env python3
import argparse
import csv
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import urllib.parse
import urllib.request

EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

ACCESSION_PATTERNS = {
    "GSE": r"\bGSE\d{3,}\b",
    "GSM": r"\bGSM\d{3,}\b",
    "SRP": r"\bSRP\d{3,}\b",
    "SRX": r"\bSRX\d{3,}\b",
    "SRR": r"\bSRR\d{3,}\b",
    "SRS": r"\bSRS\d{3,}\b",
    "PRJNA": r"\bPRJNA\d{3,}\b",
    "PRJEB": r"\bPRJEB\d{3,}\b",
    "E-MTAB": r"\bE-MTAB-\d+\b",
    "EGAS": r"\bEGAS\d{3,}\b",
    "CRA": r"\bCRA\d{3,}\b",
    "HRA": r"\bHRA\d{3,}\b",
}

DATA_TYPE_HINTS = {
    "scRNA": [r"\bscrna\b", r"single[-\s]?cell", r"single cell rna"],
    "RNA-seq": [r"\brna[-\s]?seq\b", r"transcriptome"],
    "WES": [r"\bwes\b", r"whole exome"],
    "WGS": [r"\bwgs\b", r"whole genome"],
    "ATAC-seq": [r"\batac[-\s]?seq\b"],
}


@dataclass
class RepositoryInfo:
    repository: str
    downloadable: str
    url_template: str


REPOSITORY_MAP: Dict[str, RepositoryInfo] = {
    "GSE": RepositoryInfo("GEO", "yes", "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={acc}"),
    "GSM": RepositoryInfo("GEO", "yes", "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={acc}"),
    "SRP": RepositoryInfo("SRA", "yes", "https://www.ncbi.nlm.nih.gov/sra/?term={acc}"),
    "SRX": RepositoryInfo("SRA", "yes", "https://www.ncbi.nlm.nih.gov/sra/?term={acc}"),
    "SRR": RepositoryInfo("SRA", "yes", "https://www.ncbi.nlm.nih.gov/sra/?term={acc}"),
    "SRS": RepositoryInfo("SRA", "yes", "https://www.ncbi.nlm.nih.gov/sra/?term={acc}"),
    "PRJNA": RepositoryInfo("BioProject", "yes", "https://www.ncbi.nlm.nih.gov/bioproject/{acc}"),
    "PRJEB": RepositoryInfo("ENA BioProject", "yes", "https://www.ebi.ac.uk/ena/browser/view/{acc}"),
    "E-MTAB": RepositoryInfo("ArrayExpress", "yes", "https://www.ebi.ac.uk/biostudies/arrayexpress/studies/{acc}"),
    "EGAS": RepositoryInfo("EGA", "no", "https://ega-archive.org/studies/{acc}"),
    "CRA": RepositoryInfo("GSA-Human/Genome Sequence Archive", "unknown", "https://ngdc.cncb.ac.cn/search/?dbId=gsa&q={acc}"),
    "HRA": RepositoryInfo("HRA", "unknown", "https://ngdc.cncb.ac.cn/search/?dbId=hra&q={acc}"),
}


def build_query(keyword: str, days_back: int) -> str:
    date_from = (dt.date.today() - dt.timedelta(days=days_back)).strftime("%Y-%m-%d")
    return f"({keyword}) AND FIRST_PDATE:[{date_from} TO *]"


def search_europe_pmc(keyword: str, days_back: int, page_size: int, max_pages: int) -> List[dict]:
    query = build_query(keyword, days_back)
    results: List[dict] = []

    for page in range(1, max_pages + 1):
        params = {
            "query": query,
            "format": "json",
            "pageSize": page_size,
            "page": page,
            "resultType": "core",
        }
        url = EUROPE_PMC_SEARCH_URL + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        page_results = payload.get("resultList", {}).get("result", [])
        if not page_results:
            break

        results.extend(page_results)

        if len(page_results) < page_size:
            break

    return results


def extract_accessions(text: str) -> Set[str]:
    found: Set[str] = set()
    for pattern in ACCESSION_PATTERNS.values():
        for match in re.findall(pattern, text or "", flags=re.IGNORECASE):
            found.add(match.upper())
    return found


def infer_data_type(text: str) -> str:
    normalized = (text or "").lower()
    hit = [name for name, pats in DATA_TYPE_HINTS.items() if any(re.search(p, normalized) for p in pats)]
    return ";".join(hit) if hit else "unknown"


def classify_accession(accession: str) -> Tuple[str, str, str]:
    prefix = "E-MTAB" if accession.startswith("E-MTAB-") else re.match(r"^[A-Z]+", accession).group(0)
    info = REPOSITORY_MAP.get(prefix)
    if not info:
        return "unknown", "unknown", ""
    return info.repository, info.downloadable, info.url_template.format(acc=accession)


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"seen_papers": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def iter_rows(papers: Iterable[dict], keyword: str, state: dict) -> List[dict]:
    seen = set(state.get("seen_papers", []))
    now = dt.datetime.now().isoformat(timespec="seconds")
    rows = []

    for paper in papers:
        paper_id = paper.get("id") or paper.get("pmid") or ""
        if not paper_id:
            continue
        if paper_id in seen:
            continue

        text_blobs = [
            paper.get("title", ""),
            paper.get("abstractText", ""),
            " ".join((paper.get("keywordList") or {}).get("keyword", [])) if isinstance(paper.get("keywordList"), dict) else "",
        ]
        merged_text = "\n".join(text_blobs)
        accessions = sorted(extract_accessions(merged_text))
        data_type = infer_data_type(merged_text)

        if not accessions:
            rows.append(
                {
                    "paper_id": paper_id,
                    "title": paper.get("title", ""),
                    "journal": paper.get("journalTitle", ""),
                    "pub_year": paper.get("pubYear", ""),
                    "authors": paper.get("authorString", ""),
                    "doi": paper.get("doi", ""),
                    "source": paper.get("source", ""),
                    "first_seen_at": now,
                    "keyword": keyword,
                    "accession": "",
                    "data_type_hint": data_type,
                    "downloadable": "unknown",
                    "repository": "unknown",
                    "download_url": "",
                }
            )
        else:
            for acc in accessions:
                repository, downloadable, url = classify_accession(acc)
                rows.append(
                    {
                        "paper_id": paper_id,
                        "title": paper.get("title", ""),
                        "journal": paper.get("journalTitle", ""),
                        "pub_year": paper.get("pubYear", ""),
                        "authors": paper.get("authorString", ""),
                        "doi": paper.get("doi", ""),
                        "source": paper.get("source", ""),
                        "first_seen_at": now,
                        "keyword": keyword,
                        "accession": acc,
                        "data_type_hint": data_type,
                        "downloadable": downloadable,
                        "repository": repository,
                        "download_url": url,
                    }
                )

        seen.add(paper_id)

    state["seen_papers"] = sorted(seen)
    return rows


def write_csv(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    headers = [
        "paper_id",
        "title",
        "journal",
        "pub_year",
        "authors",
        "doi",
        "source",
        "first_seen_at",
        "keyword",
        "accession",
        "data_type_hint",
        "downloadable",
        "repository",
        "download_url",
    ]

    file_exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        for row in rows:
            writer.writerow(row)


def run_collect(args: argparse.Namespace) -> None:
    state_path = Path(args.state)
    out_path = Path(args.out)

    state = load_state(state_path)
    papers = search_europe_pmc(args.keyword, args.days_back, args.page_size, args.max_pages)
    rows = iter_rows(papers, args.keyword, state)

    if rows:
        write_csv(out_path, rows)
    save_state(state_path, state)

    print(f"papers_fetched={len(papers)} new_rows={len(rows)} out={out_path}")


def run_collect_from_config(args: argparse.Namespace) -> None:
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    namespace = argparse.Namespace(
        keyword=cfg["keyword"],
        days_back=cfg.get("days_back", 365),
        out=cfg["out"],
        state=cfg["state"],
        page_size=cfg.get("page_size", 100),
        max_pages=cfg.get("max_pages", 20),
    )
    run_collect(namespace)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect public cancer-related papers and downloadable dataset links.")
    sub = parser.add_subparsers(required=True)

    collect = sub.add_parser("collect", help="Run one collection task.")
    collect.add_argument("--keyword", required=True)
    collect.add_argument("--days-back", type=int, default=365)
    collect.add_argument("--out", required=True)
    collect.add_argument("--state", required=True)
    collect.add_argument("--page-size", type=int, default=100)
    collect.add_argument("--max-pages", type=int, default=20)
    collect.set_defaults(func=run_collect)

    collect_cfg = sub.add_parser("collect-from-config", help="Run collection from JSON config file.")
    collect_cfg.add_argument("--config", required=True)
    collect_cfg.set_defaults(func=run_collect_from_config)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

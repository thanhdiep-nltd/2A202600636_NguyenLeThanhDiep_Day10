from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import time
import requests

from core.config import Settings
from core.utils import write_json, read_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    def clean_abstract(abstract_str: str | None) -> str:
        if not abstract_str:
            return ""
        # Clean XML/HTML tags and comments
        cleaned = re.sub(r"<!--.*?-->", "", abstract_str, flags=re.DOTALL)
        cleaned = re.sub(r"</?[a-zA-Z0-9:]+[^>]*>", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned.lower().startswith("abstract "):
            cleaned = cleaned[9:].strip()
        elif cleaned.lower().startswith("abstract:"):
            cleaned = cleaned[9:].strip()
        return cleaned

    def extract_date(item: dict, keys: list[str]) -> str:
        for key in keys:
            date_dict = item.get(key)
            if date_dict and "date-parts" in date_dict:
                parts = date_dict["date-parts"]
                if parts and isinstance(parts, list) and isinstance(parts[0], list):
                    date_parts = parts[0]
                    if date_parts:
                        year = date_parts[0] if len(date_parts) > 0 else None
                        month = date_parts[1] if len(date_parts) > 1 else 1
                        day = date_parts[2] if len(date_parts) > 2 else 1
                        if year is not None:
                            return f"{year:04d}-{month:02d}-{day:02d}"
        return ""

    for item in items:
        # 1. DOI
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        # 2. Title
        title_list = item.get("title", [])
        title = title_list[0].strip() if title_list else ""
        if not title:
            continue

        # 3. Summary (Abstract)
        summary = clean_abstract(item.get("abstract", ""))

        # 4. Authors
        authors: list[str] = []
        for auth in item.get("author", []):
            given = auth.get("given", "").strip()
            family = auth.get("family", "").strip()
            if given and family:
                name = f"{given} {family}"
            elif family:
                name = family
            elif given:
                name = given
            else:
                name = ""
            if name:
                authors.append(name)

        # 5. Categories
        categories = [sub.strip() for sub in item.get("subject", []) if sub.strip()]
        primary_category = categories[0] if categories else "unknown"

        # 6. Dates
        published = extract_date(item, ["published-print", "published-online", "created"])
        if not published:
            published = "2026-06-10"

        updated = extract_date(item, ["updated", "indexed"])
        if not updated:
            updated = published

        # 7. URLs
        abs_url = item.get("URL", "").strip()
        if not abs_url:
            abs_url = f"https://doi.org/{doi}"

        pdf_url = ""
        for link in item.get("link", []):
            link_url = link.get("URL", "").strip()
            content_type = link.get("content-type", "").lower()
            if "pdf" in content_type or link_url.endswith(".pdf"):
                pdf_url = link_url
                break
        if not pdf_url and item.get("link"):
            pdf_url = item["link"][0].get("URL", "").strip()

        # 8. Comment
        container_list = item.get("container-title", [])
        comment = container_list[0].strip() if container_list else ""

        records.append(
            PaperRecord(
                paper_id=doi,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi source API, luu raw response, parse thanh records.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    url = "https://api.crossref.org/works"
    headers = {
        "User-Agent": "Day10DataObservabilityLab/1.0 (mailto:student@example.com)"
    }

    max_retries = 3
    backoff = 2.0
    payload = None

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            if response.status_code == 200:
                payload = response.json()
                break
            elif response.status_code in (429, 503):
                time.sleep(backoff * (2**attempt))
            else:
                response.raise_for_status()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(backoff * (2**attempt))

    if payload is None:
        raise RuntimeError("Failed to fetch data from Crossref API after retries.")

    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)

    records_dict = [
        {
            "paper_id": r.paper_id,
            "title": r.title,
            "summary": r.summary,
            "authors": r.authors,
            "categories": r.categories,
            "primary_category": r.primary_category,
            "published": r.published,
            "updated": r.updated,
            "abs_url": r.abs_url,
            "pdf_url": r.pdf_url,
            "comment": r.comment,
        }
        for r in records
    ]
    write_json(settings.paths.raw_records_json, records_dict)

    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    if not path.exists():
        raise FileNotFoundError(f"Raw records file not found at {path}")
    raw_list = read_json(path)
    records = []
    for item in raw_list:
        records.append(
            PaperRecord(
                paper_id=item["paper_id"],
                title=item["title"],
                summary=item["summary"],
                authors=item["authors"],
                categories=item["categories"],
                primary_category=item["primary_category"],
                published=item["published"],
                updated=item["updated"],
                abs_url=item["abs_url"],
                pdf_url=item["pdf_url"],
                comment=item["comment"],
            )
        )
    return records


if __name__ == "__main__":
    import sys
    # Add src directory to PYTHONPATH automatically if running directly
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from core.config import load_settings
    
    print("Loading settings...")
    settings = load_settings()
    print(f"Fetching papers from Crossref API...")
    print(f"Query: {settings.source_query}")
    print(f"Filter: {settings.source_filter}")
    print(f"Max results: {settings.max_results}")
    
    try:
        records = fetch_source_records(settings)
        print(f"\nSuccessfully fetched {len(records)} records!")
        if records:
            print("\nSample Paper Record:")
            r = records[0]
            print(f"ID: {r.paper_id}")
            print(f"Title: {r.title}")
            print(f"Published: {r.published}")
            print(f"Authors: {r.authors}")
            print(f"Categories: {r.categories}")
            print(f"Summary (first 150 chars): {r.summary[:150]}...")
    except Exception as e:
        print(f"Error occurred: {e}", file=sys.stderr)

"""Collect public knowledge about Biblio 79 Ngụy Như Kon Tum.

    uv run python scripts/knowledge/collect.py web                 # free: fetch public pages listed in sources.json
    uv run python scripts/knowledge/collect.py google-maps         # paid (bounded): 1 place + <=30 reviews
    uv run python scripts/knowledge/collect.py tiktok              # paid (bounded): <=20 videos
    uv run python scripts/knowledge/collect.py tiktok --from-run <RUN_ID>   # re-download an existing run, no new charge

Guarantees:
- Each Apify run passes max_total_charge_usd (hard cap enforced by Apify for pay-per-event actors).
- A successful run is never repeated unless --force is given (raw/apify/<name>/run_meta.json exists).
- Failed runs are NOT retried automatically.
- Reviewer personal data is not requested (scrapeReviewsPersonalData=false) and is stripped again before saving.
Raw outputs go to data/knowledge/raw/ (gitignored). Secrets come from the repo-root .env and are never printed.
"""
from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _paths import RAW_APIFY_DIR, RAW_WEB_DIR, SOURCES_CONFIG, read_json, utc_now, write_json  # noqa: E402

from app.settings import load_settings  # noqa: E402

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
KEYWORDS = ("biblio", "ngụy như kon tum", "nguy nhu kon tum", "tam khương", "xa la", "hacinco")


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template"}
    BLOCK = {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "tr", "section", "article", "header", "footer"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> tuple[str, str]:
    parser = _TextExtractor()
    parser.feed(html)
    lines = [" ".join(line.split()) for line in "".join(parser.parts).splitlines()]
    return parser.title.strip(), "\n".join(line for line in lines if line)


def keyword_excerpts(text: str, window: int = 700) -> list[str]:
    low = text.lower()
    spans: list[tuple[int, int]] = []
    for kw in KEYWORDS:
        start = 0
        while (idx := low.find(kw, start)) != -1:
            spans.append((max(0, idx - window), min(len(text), idx + window)))
            start = idx + len(kw)
    spans.sort()
    merged: list[list[int]] = []
    for s, e in spans:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [text[s:e] for s, e in merged]


def collect_web(force: bool) -> None:
    config = read_json(SOURCES_CONFIG)
    log: list[dict] = []
    with httpx.Client(timeout=25, follow_redirects=True, headers={"User-Agent": USER_AGENT, "Accept-Language": "vi,en;q=0.8"}) as client:
        for src in config["web"]:
            out_txt = RAW_WEB_DIR / f"{src['id']}.txt"
            if out_txt.exists() and not force:
                log.append({**src, "status": "cached"})
                continue
            entry = {**src, "fetched_at": utc_now()}
            try:
                resp = client.get(src["url"])
                entry["http_status"] = resp.status_code
                entry["final_url"] = str(resp.url)
                if resp.status_code == 200 and "html" in resp.headers.get("content-type", ""):
                    title, text = html_to_text(resp.text)
                    excerpts = keyword_excerpts(text)
                    RAW_WEB_DIR.mkdir(parents=True, exist_ok=True)
                    (RAW_WEB_DIR / f"{src['id']}.html").write_text(resp.text, encoding="utf-8")
                    out_txt.write_text(text, encoding="utf-8")
                    write_json(RAW_WEB_DIR / f"{src['id']}.excerpts.json", {"title": title, "url": src["url"], "excerpts": excerpts})
                    entry.update(status="ok", title=title, text_chars=len(text), excerpt_count=len(excerpts))
                else:
                    entry["status"] = "http_error"
            except httpx.HTTPError as exc:
                entry.update(status="transport_error", error=type(exc).__name__)
            log.append(entry)
            print(f"[web] {src['id']}: {entry.get('status')} {entry.get('http_status', '')} excerpts={entry.get('excerpt_count', 0)}")
    write_json(RAW_WEB_DIR / "fetch_log.json", log)


_GMAPS_PLACE_KEEP = (
    "title", "subTitle", "description", "categoryName", "categories", "address", "street", "city", "state",
    "countryCode", "location", "plusCode", "phone", "phoneUnformatted", "website", "menu", "price", "openingHours",
    "additionalOpeningHours", "additionalInfo", "totalScore", "reviewsCount", "reviewsDistribution", "placeId",
    "cid", "fid", "url", "searchString", "permanentlyClosed", "temporarilyClosed", "popularTimesLiveText",
    "peopleAlsoSearch", "reviewsTags", "ownerUpdates", "questionsAndAnswers",
)
_GMAPS_REVIEW_KEEP = (
    "text", "textTranslated", "originalLanguage", "stars", "rating", "publishedAtDate", "publishAt", "likesCount",
    "reviewId", "reviewUrl", "responseFromOwnerText", "responseFromOwnerDate", "reviewContext", "reviewDetailedRating",
)
_TIKTOK_KEEP = (
    "id", "text", "textLanguage", "createTimeISO", "webVideoUrl", "playCount", "diggCount", "shareCount",
    "commentCount", "collectCount", "isAd", "isSponsored", "searchQuery", "locationMeta", "isPinned",
)


def _sanitize_gmaps(item: dict) -> dict:
    place = {k: item.get(k) for k in _GMAPS_PLACE_KEEP if k in item}
    place["reviews"] = [{k: r.get(k) for k in _GMAPS_REVIEW_KEEP if k in r} for r in item.get("reviews") or []]
    return place


def _sanitize_tiktok(item: dict) -> dict:
    out = {k: item.get(k) for k in _TIKTOK_KEEP if k in item}
    author = item.get("authorMeta") or {}
    out["author_handle"] = author.get("name")  # public creator handle, needed to spot official accounts
    out["author_verified"] = author.get("verified")
    out["hashtags"] = [h.get("name") for h in item.get("hashtags") or [] if isinstance(h, dict)]
    return out


def _run_summary(run) -> dict:
    data = run.model_dump(mode="json") if hasattr(run, "model_dump") else dict(run)
    keep = ("id", "act_id", "status", "started_at", "finished_at", "default_dataset_id", "usage_total_usd",
            "charged_event_counts", "status_message", "build_number")
    return {k: data.get(k) for k in keep}


def collect_apify(name: str, force: bool, from_run: str | None) -> None:
    from apify_client import ApifyClient

    settings = load_settings()
    if not settings.apify_api_token:
        raise SystemExit("APIFY_API_TOKEN missing in .env")
    cfg = read_json(SOURCES_CONFIG)["apify"]
    actor_cfg = cfg["google_maps" if name == "google-maps" else "tiktok"]
    out_dir = RAW_APIFY_DIR / name
    meta_path = out_dir / "run_meta.json"
    if meta_path.exists() and not force and not from_run:
        print(f"[apify:{name}] run_meta.json exists -> skipping new run (use --force or --from-run)")
        return

    client = ApifyClient(settings.apify_api_token)
    if from_run:
        run = client.run(from_run).get()
        if run is None:
            raise SystemExit(f"Run {from_run} not found")
    else:
        cap = Decimal(str(actor_cfg["max_total_charge_usd"]))
        caps_sum = Decimal(str(cfg["google_maps"]["max_total_charge_usd"])) + Decimal(str(cfg["tiktok"]["max_total_charge_usd"]))
        if caps_sum > Decimal(str(cfg["budget_usd_total"])):
            raise SystemExit(f"Sum of per-run caps ({caps_sum}) exceeds total Apify budget")
        print(f"[apify:{name}] starting {actor_cfg['actor_id']} with max_total_charge_usd={cap}")
        run = client.actor(actor_cfg["actor_id"]).call(
            run_input=actor_cfg["input"],
            max_items=actor_cfg.get("max_items"),
            max_total_charge_usd=cap,
            run_timeout=timedelta(minutes=10),
        )
        if run is None:
            raise SystemExit("Actor call returned no run")
    summary = _run_summary(run)
    summary.update(actor_id=actor_cfg["actor_id"], input=actor_cfg["input"], collected_at=utc_now(),
                   max_total_charge_usd=actor_cfg["max_total_charge_usd"])
    items = list(client.dataset(summary["default_dataset_id"]).list_items(clean=True).items) if summary.get("default_dataset_id") else []
    sanitized = [_sanitize_gmaps(i) if name == "google-maps" else _sanitize_tiktok(i) for i in items]
    # Re-read the run after dataset fetch so usage_total_usd reflects final accounting.
    final = client.run(summary["id"]).get()
    if final is not None:
        summary.update({k: v for k, v in _run_summary(final).items() if v is not None})
    summary["item_count"] = len(sanitized)
    write_json(out_dir / "items.json", sanitized)
    write_json(meta_path, summary)
    print(f"[apify:{name}] status={summary.get('status')} items={len(sanitized)} usage_total_usd={summary.get('usage_total_usd')} run_id={summary.get('id')}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("target", choices=["web", "google-maps", "tiktok"])
    parser.add_argument("--force", action="store_true", help="re-fetch / re-run even if cached")
    parser.add_argument("--from-run", help="download dataset of an existing Apify run instead of starting a new one")
    args = parser.parse_args()
    if args.target == "web":
        collect_web(args.force)
    else:
        collect_apify(args.target, args.force, args.from_run)


if __name__ == "__main__":
    main()

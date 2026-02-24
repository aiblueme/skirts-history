#!/usr/bin/env python3
"""
fashion_crawler.py
──────────────────
Automates image collection for the Skirts History research project.

For each era in research.json, this script:
  1. Creates assets/<era_index>_<slug>/
  2. Runs BingImageCrawler   → 3 images per query
  3. Waits 3 s (engine-switch delay)
  4. Runs BaiduImageCrawler  → 3 images per query
  5. Applies a randomised jitter (2–5 s) before the next query

Stealth features:
  - Random User-Agent per crawler instance (pool of 10)
  - parser_threads=1 / downloader_threads=1 (low-profile throttle)
  - Custom Accept-Language + engine-appropriate Referer header
  - Request jitter between every query cycle

Usage:
    python fashion_crawler.py

Outputs:
    assets/<XX>_<slug>/        — sequential icrawler images (000001.jpg …)
    scrape_status.log          — INFO+ events; WARNING/ERROR for blocks & failures
    completed_queries.json     — checkpoint; delete to force a full re-run

Resume behaviour:
    Re-running the script skips any query already recorded in the checkpoint.
    A query is marked complete once at least one engine fetches images for it.
    Queries where both engines failed (network/block) are left unmarked and
    will be retried on the next run.
    Delete completed_queries.json to start entirely from scratch.
"""

import json
import logging
import random
import re
import sys
import time
from pathlib import Path

from icrawler.builtin import BaiduImageCrawler, BingImageCrawler

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

RESEARCH_FILE      = "research.json"
ASSETS_DIR         = "assets"
LOG_FILE           = "scrape_status.log"
CHECKPOINT_FILE    = "completed_queries.json"

IMAGES_PER_ENGINE  = 3      # images fetched per engine, per query
INTER_ENGINE_DELAY = 3      # fixed seconds between Bing → Baidu
JITTER_MIN         = 2.0    # minimum jitter seconds between query cycles
JITTER_MAX         = 5.0    # maximum jitter seconds between query cycles

IMAGE_EXTENSIONS   = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

# ─────────────────────────────────────────────────────────────────────────────
# User-Agent pool — 10 modern browser strings, rotated randomly per instance
# ─────────────────────────────────────────────────────────────────────────────

USER_AGENTS: list[str] = [
    # Chrome 124 – Windows 10
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",

    # Edge 123 – Windows 10
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 "
    "Edg/123.0.2420.81",

    # Chrome 124 – macOS Sonoma
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",

    # Firefox 125 – Windows 10
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",

    # Safari 17 – macOS Sonoma
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",

    # Chrome 124 – Ubuntu Linux
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",

    # Opera GX 109 – Windows 10
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
    "OPR/109.0.0.0",

    # Edge 123 – macOS Sonoma
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 "
    "Edg/123.0.2420.81",

    # Firefox 125 – Ubuntu Linux
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:125.0) "
    "Gecko/20100101 Firefox/125.0",

    # Vivaldi 6.7 – Windows 10
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
    "Vivaldi/6.7.3329.21",
]

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# Writes INFO+ to the console and to scrape_status.log.
# icrawler's own logger (WARNING+) is also routed here, so 403/429 messages
# from the library's internal downloader appear in the log file automatically.
# ─────────────────────────────────────────────────────────────────────────────

def _configure_logging() -> logging.Logger:
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File: captures everything including icrawler's internal 403/429 messages
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(fmt)

    # Console: only our own logger's messages — suppresses icrawler thread noise
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)
    console_handler.addFilter(lambda r: r.name.startswith("fashion_crawler"))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    # icrawler WARNING+ still reaches the file handler via root propagation
    logging.getLogger("icrawler").setLevel(logging.WARNING)

    return logging.getLogger("fashion_crawler")


logger = _configure_logging()

# ─────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    """'Ancient Egypt and Mesopotamia' → 'ancient_egypt_and_mesopotamia'"""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)     # strip punctuation
    text = re.sub(r"[\s_]+", "_", text)     # collapse whitespace / underscores
    return text.strip("_")


def build_era_folder(era: dict, base: Path) -> Path:
    """Construct, create, and return the save directory for one era.

    Naming: assets/<zero-padded-index>_<slug>/
    Example: assets/01_ancient_egypt_and_mesopotamia/
    """
    raw_idx = era["era_index"]
    idx_str = str(raw_idx).zfill(2) if isinstance(raw_idx, int) else str(raw_idx)
    folder  = base / f"{idx_str}_{slugify(era['title'])}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def count_images(directory: str) -> int:
    """Return the number of image files already saved in *directory*.

    Passed as `file_idx_offset` to each crawler so sequential filenames
    (000001.jpg …) never collide across multiple engine / query calls
    within the same era folder.
    """
    return sum(
        1 for p in Path(directory).iterdir()
        if p.suffix.lower() in IMAGE_EXTENSIONS
    )


def stealth_headers(referer: str, lang: str = "en-US,en;q=0.9") -> dict[str, str]:
    """Build a randomised stealth header dict for one crawler instance.

    Pass lang='zh-CN,zh;q=0.9' for Baidu to improve relevance of results.
    """
    return {
        "User-Agent":      random.choice(USER_AGENTS),
        "Accept-Language": lang,
        "Referer":         referer,
    }


def _inject_headers(crawler, headers: dict[str, str]) -> None:
    """Push custom headers into the crawler's shared requests.Session."""
    if hasattr(crawler, "session"):
        crawler.session.headers.update(headers)
    else:
        logger.debug("Crawler has no .session attribute — header injection skipped.")


# Substrings that signal an HTTP 403 / 429 rate-limit block
_BLOCK_SIGNALS = frozenset((
    "403", "429", "forbidden", "too many requests", "rate limit", "rate-limit",
))


def _is_blocked(exc: Exception) -> bool:
    return any(sig in str(exc).lower() for sig in _BLOCK_SIGNALS)


# ─────────────────────────────────────────────────────────────────────────────
# Checkpoint — persist completed queries so interrupted runs can resume
#
# File format (completed_queries.json):
#   {
#     "01_ancient_egypt_and_mesopotamia": [
#       "query string A",
#       "query string B"
#     ],
#     ...
#   }
# The key is the era folder name; the value is the list of completed queries.
# Delete the file (or a specific key) to force re-processing.
# ─────────────────────────────────────────────────────────────────────────────

# Type alias for the in-memory checkpoint dict
Checkpoint = dict[str, list[str]]


def load_checkpoint() -> Checkpoint:
    """Load completed_queries.json.  Returns {} if the file is absent or corrupt."""
    path = Path(CHECKPOINT_FILE)
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            return data
        logger.warning("Checkpoint file has unexpected format — starting fresh.")
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Checkpoint file unreadable (%s) — starting fresh.", exc)
    return {}


def save_checkpoint(checkpoint: Checkpoint) -> None:
    """Write the checkpoint atomically via a temp-file → rename so a mid-write
    kill (Ctrl-C, SIGTERM) never leaves a corrupt file on disk."""
    tmp = Path(CHECKPOINT_FILE).with_suffix(".tmp")
    try:
        tmp.write_text(
            json.dumps(checkpoint, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.rename(CHECKPOINT_FILE)
    except OSError as exc:
        logger.error("Could not save checkpoint: %s", exc)


def is_done(checkpoint: Checkpoint, era_key: str, query: str) -> bool:
    """Return True if *query* is already recorded as complete for *era_key*."""
    return query in checkpoint.get(era_key, [])


def mark_done(checkpoint: Checkpoint, era_key: str, query: str) -> None:
    """Record *query* as complete and flush the checkpoint to disk immediately."""
    completed = checkpoint.setdefault(era_key, [])
    if query not in completed:
        completed.append(query)
    save_checkpoint(checkpoint)


# ─────────────────────────────────────────────────────────────────────────────
# Engine runners
# ─────────────────────────────────────────────────────────────────────────────

def crawl_bing(query: str, save_dir: str, file_idx_offset: int) -> None:
    """Fetch IMAGES_PER_ENGINE images from Bing for a single query."""
    crawler = BingImageCrawler(
        storage={"root_dir": save_dir},
        parser_threads=1,
        downloader_threads=1,
    )
    _inject_headers(crawler, stealth_headers("https://www.bing.com/"))
    crawler.crawl(
        keyword=query,
        max_num=IMAGES_PER_ENGINE,
        file_idx_offset=file_idx_offset,
    )


def _extend_session_timeout(crawler, seconds: int = 20) -> None:
    """Wrap session.send so every request uses at least *seconds* as timeout.

    Baidu's CDN is geo-restricted; icrawler's default 5 s connect timeout
    causes frequent first-attempt failures that burn retries and add ~30 s
    per Baidu call. This patch raises the floor without touching icrawler internals.
    """
    if not hasattr(crawler, "session"):
        return
    original_send = crawler.session.send

    def _send(request, **kwargs):
        kwargs["timeout"] = seconds
        return original_send(request, **kwargs)

    crawler.session.send = _send


def crawl_baidu(query: str, save_dir: str, file_idx_offset: int) -> None:
    """Fetch IMAGES_PER_ENGINE images from Baidu for a single query."""
    crawler = BaiduImageCrawler(
        storage={"root_dir": save_dir},
        parser_threads=1,
        downloader_threads=1,
    )
    _inject_headers(
        crawler,
        stealth_headers("https://image.baidu.com/", lang="zh-CN,zh;q=0.9"),
    )
    _extend_session_timeout(crawler, seconds=20)
    crawler.crawl(
        keyword=query,
        max_num=IMAGES_PER_ENGINE,
        file_idx_offset=file_idx_offset,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────────────────────────────────────

# Return tokens from run_engine
_OK         = "ok"
_SKIP_QUERY = "skip_query"   # move on to the next query
_SKIP_ERA   = "skip_era"     # abort the whole era


def run_engine(
    engine_name: str,
    fn,
    query: str,
    save_dir: str,
    offset: int,
) -> str:
    """Execute one crawler engine for a single query with full error handling.

    Returns one of: _OK | _SKIP_QUERY | _SKIP_ERA
    """
    try:
        fn(query, save_dir, offset)
        logger.info("      [%s] OK — '%s'", engine_name, query)
        return _OK

    except (ConnectionError, TimeoutError) as exc:
        if _is_blocked(exc):
            logger.warning(
                "      [%s] BLOCKED (403/429) on query '%s' — skipping query. (%s)",
                engine_name, query, exc,
            )
        else:
            logger.error(
                "      [%s] Network/Timeout error on query '%s' — skipping query. (%s)",
                engine_name, query, exc,
            )
        return _SKIP_QUERY

    except Exception as exc:  # noqa: BLE001
        if _is_blocked(exc):
            logger.warning(
                "      [%s] BLOCKED (403/429) on query '%s' — skipping entire era. (%s)",
                engine_name, query, exc,
            )
            return _SKIP_ERA
        logger.error(
            "      [%s] Unexpected error on query '%s' — skipping query. (%s)",
            engine_name, query, exc,
        )
        return _SKIP_QUERY


def process_era(era: dict, base_dir: Path, checkpoint: Checkpoint) -> None:
    """Download images for every query belonging to a single era."""
    title   = era.get("title", "unknown")
    queries = era.get("icrawler_queries", [])
    total   = len(queries)

    folder   = build_era_folder(era, base_dir)
    save_dir = str(folder)
    era_key  = folder.name      # e.g. "01_ancient_egypt_and_mesopotamia"

    already_done = sum(1 for q in queries if is_done(checkpoint, era_key, q))

    # ── Short-circuit: entire era already finished ─────────────────────────────
    if already_done == total:
        logger.info(
            "=== Era: %s — SKIP (all %d quer%s in checkpoint) ===",
            title, total, "y" if total == 1 else "ies",
        )
        return

    logger.info(
        "=== Era: %s  (%d quer%s, %d done) ===",
        title, total, "y" if total == 1 else "ies", already_done,
    )
    logger.info("    Save dir : %s", save_dir)

    for i, query in enumerate(queries, start=1):

        # ── Skip already-completed queries ────────────────────────────────────
        if is_done(checkpoint, era_key, query):
            logger.info("  -- Query [%d/%d]: SKIP (checkpoint) '%s'", i, total, query)
            continue

        logger.info("  -- Query [%d/%d]: '%s'", i, total, query)

        # ── Bing ──────────────────────────────────────────────────────────────
        offset      = count_images(save_dir)
        bing_result = run_engine("Bing", crawl_bing, query, save_dir, offset)

        if bing_result == _SKIP_ERA:
            logger.warning("    Hard block on Bing — aborting era '%s'.", title)
            return

        # ── Fixed engine-switch delay ──────────────────────────────────────────
        logger.info(
            "      Sleeping %ds (engine switch: Bing -> Baidu)...",
            INTER_ENGINE_DELAY,
        )
        time.sleep(INTER_ENGINE_DELAY)

        # ── Baidu ─────────────────────────────────────────────────────────────
        offset       = count_images(save_dir)
        baidu_result = run_engine("Baidu", crawl_baidu, query, save_dir, offset)

        if baidu_result == _SKIP_ERA:
            logger.warning("    Hard block on Baidu — aborting era '%s'.", title)
            return

        # ── Checkpoint: mark done if at least one engine fetched images ────────
        # Queries where both engines failed are left unmarked for automatic retry.
        if _OK in (bing_result, baidu_result):
            mark_done(checkpoint, era_key, query)
            logger.info("      Checkpoint saved — '%s'", query)

        # ── Query-cycle jitter (omit after the final query) ───────────────────
        if i < total:
            jitter = random.uniform(JITTER_MIN, JITTER_MAX)
            logger.info("      Jitter %.2fs before next query...", jitter)
            time.sleep(jitter)

    logger.info("    Era '%s' complete.", title)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    research_path = Path(RESEARCH_FILE)
    if not research_path.exists():
        logger.error(
            "'%s' not found in '%s'. Place it next to this script and retry.",
            RESEARCH_FILE, Path.cwd(),
        )
        sys.exit(1)

    with research_path.open(encoding="utf-8") as fh:
        raw = json.load(fh)

    # Accept both a bare list [ {...}, ... ] and a {"eras": [...]} wrapper
    eras: list[dict] = raw if isinstance(raw, list) else raw.get("eras", [])

    if not eras:
        logger.error(
            "No eras found in '%s'. Expected a JSON array or {\"eras\": [...]}.",
            RESEARCH_FILE,
        )
        sys.exit(1)

    base_dir = Path(ASSETS_DIR)
    base_dir.mkdir(exist_ok=True)

    checkpoint   = load_checkpoint()
    total_done   = sum(len(v) for v in checkpoint.values())
    total_queries = sum(len(e.get("icrawler_queries", [])) for e in eras)

    logger.info("Fashion Image Crawler — starting.  Eras: %d", len(eras))
    logger.info("Output root  : %s", base_dir.resolve())
    logger.info("Status log   : %s", Path(LOG_FILE).resolve())
    logger.info("Checkpoint   : %s", Path(CHECKPOINT_FILE).resolve())
    if total_done:
        logger.info(
            "Resuming     : %d / %d quer%s already complete — will skip those.",
            total_done, total_queries,
            "y" if total_queries == 1 else "ies",
        )
    else:
        logger.info("Checkpoint   : empty — fresh run.")

    for era in eras:
        process_era(era, base_dir, checkpoint)

    logger.info(
        "All eras processed. Review '%s' for any blocked / error events.", LOG_FILE
    )


if __name__ == "__main__":
    main()

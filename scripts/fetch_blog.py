#!/usr/bin/env python3
"""네이버 블로그 RSS를 받아 assets/blog.json 으로 저장합니다.

GitHub Actions(.github/workflows/blog-feed.yml)에서 주기적으로 실행됩니다.
지정 카테고리에 글이 없으면 블로그 전체 피드로 대신 채웁니다.
"""
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

BLOG_ID = "kcwlove12"
CATEGORY_NO = "6"
MAX_ITEMS = 8
OUT = Path(__file__).resolve().parent.parent / "assets" / "blog.json"
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (compatible; ysdnc-blog-feed/1.0; +https://ysdnc.co.kr)"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    items = []
    for it in root.iter("item"):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        link = re.sub(r"\?.*$", "", link)  # fromRss/trackingCode 파라미터 제거
        date = ""
        raw = it.findtext("pubDate")
        if raw:
            try:
                date = parsedate_to_datetime(raw).astimezone(KST).strftime("%Y.%m.%d")
            except (TypeError, ValueError):
                pass
        if title and link:
            items.append({"title": title, "link": link, "date": date})
    return items


def main():
    sources = [
        f"https://rss.blog.naver.com/{BLOG_ID}.xml?categoryNo={CATEGORY_NO}",
        f"https://rss.blog.naver.com/{BLOG_ID}.xml",
    ]
    items = []
    for url in sources:
        try:
            items = parse(fetch(url))
        except Exception as e:  # 네트워크/파싱 실패 시 다음 소스로
            print(f"[warn] {url}: {e}", file=sys.stderr)
            continue
        if items:
            print(f"[ok] {url}: {len(items)} items")
            break

    if not items:
        # 실패하면 기존 파일을 그대로 둡니다(빈 목록으로 덮어쓰지 않음).
        print("[error] no items fetched; keeping existing blog.json", file=sys.stderr)
        sys.exit(0)

    data = {
        "updated": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "items": items[:MAX_ITEMS],
    }
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    new = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    # 글 목록이 바뀌었을 때만 파일을 갱신(불필요한 커밋 방지)
    if old:
        try:
            if json.loads(old).get("items") == data["items"]:
                print("[ok] no change")
                return
        except ValueError:
            pass
    OUT.write_text(new, encoding="utf-8")
    print(f"[ok] wrote {OUT}")


if __name__ == "__main__":
    main()

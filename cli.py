#!/usr/bin/env python3
"""BOBA 週報 CLI — YouTube 影片逐字稿產出工具

Pipeline:
    candidates → research → draft → publish

每週一集,以 ISO week(YYYY-WW)為單位。
"""

import os
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
WIKI_ROOT = Path("/home/node/boba-wiki")
DRAFTS = ROOT / "drafts"
EPISODES = ROOT / "episodes"
DATA = ROOT / "data"

DRAFTS.mkdir(exist_ok=True)
EPISODES.mkdir(exist_ok=True)
DATA.mkdir(exist_ok=True)


# ────────────────────────── Week helpers ──────────────────────────

def current_week() -> str:
    """Return current ISO week as 'YYYY-WW'."""
    y, w, _ = date.today().isocalendar()
    return f"{y}-{w:02d}"


def parse_week(week: str) -> tuple[int, int]:
    """Parse 'YYYY-WW' into (year, week). Raise SystemExit on bad input."""
    m = re.match(r"^(\d{4})-(\d{1,2})$", week)
    if not m:
        print(f"❌ 週別格式錯誤:{week}(應為 YYYY-WW,例如 2026-16)")
        sys.exit(1)
    y, w = int(m.group(1)), int(m.group(2))
    if not (1 <= w <= 53):
        print(f"❌ 週數 {w} 超出 1-53 範圍")
        sys.exit(1)
    return y, w


def week_dates(week: str) -> list[date]:
    """Return 7 dates (Mon-Sun) for the given ISO week."""
    y, w = parse_week(week)
    monday = date.fromisocalendar(y, w, 1)
    return [monday + timedelta(days=i) for i in range(7)]


def raw_paths_for_week(week: str) -> list[Path]:
    """List existing raw daily report paths for the week."""
    paths = []
    for d in week_dates(week):
        p = WIKI_ROOT / "raw" / f"{d.year:04d}" / f"{d.month:02d}" / f"{d.day:02d}.md"
        if p.exists():
            paths.append(p)
    return paths


# ────────────────────────── Commands ──────────────────────────

def cmd_candidates(week: str):
    """掃本週 raw 日報,列出最常被提到的 wiki entity 作為候選新聞。"""
    raws = raw_paths_for_week(week)
    if not raws:
        print(f"❌ 本週 ({week}) 沒找到任何 raw 日報")
        print(f"   預期位置:{WIKI_ROOT}/raw/YYYY/MM/DD.md")
        sys.exit(1)

    print(f"📅 掃描本週 ({week}) 的 {len(raws)} 篇日報 ...\n")

    # Count wiki entity references across the week's raw reports
    slug_hits: Counter[str] = Counter()
    slug_contexts: dict[str, list[str]] = {}  # slug → up to 3 short mentions

    for raw_path in raws:
        text = raw_path.read_text(encoding="utf-8")
        # Match [[wiki/<slug>|Label]] or [[wiki/<slug>]]
        for m in re.finditer(r"\[\[wiki/([^\]\|]+?)(?:\|[^\]]+)?\]\]", text):
            slug = m.group(1).rstrip("\\").strip()
            slug_hits[slug] += 1
            if len(slug_contexts.get(slug, [])) < 3:
                # Grab ~80 chars around the mention for flavour
                start = max(0, m.start() - 40)
                end = min(len(text), m.end() + 40)
                snippet = text[start:end].replace("\n", " ").strip()
                slug_contexts.setdefault(slug, []).append(snippet)

    if not slug_hits:
        print("❌ 本週日報沒有任何 wiki entity 引用")
        sys.exit(1)

    # Enrich with wiki page metadata
    entries = []
    for slug, hits in slug_hits.items():
        wiki_page = WIKI_ROOT / "wiki" / f"{slug}.md"
        summary, events, related = "", 0, 0
        if wiki_page.exists():
            content = wiki_page.read_text(encoding="utf-8")
            # Try to grab the first non-empty line as summary
            for line in content.splitlines():
                s = line.strip()
                if s and not s.startswith("#") and not s.startswith("---"):
                    summary = s[:80]
                    break
            events = len(re.findall(r"\*\*\d{4}-\d{2}-\d{2}\*\*", content))
            related_section = content.split("## Related")[-1] if "## Related" in content else ""
            related = len(re.findall(r"\[\[", related_section))
        entries.append({
            "slug": slug,
            "hits": hits,
            "summary": summary or "(wiki page 未建立)",
            "events": events,
            "related": related,
            # Score: this-week mentions dominate; wiki depth is tiebreaker
            "score": hits * 10 + events + related,
        })

    entries.sort(key=lambda e: e["score"], reverse=True)

    # Check what's already drafted / published
    draft_path = DRAFTS / f"{week}.md"
    episode_path = EPISODES / f"{week}.md"
    week_status = (
        "📝 本週已有草稿" if draft_path.exists()
        else "✅ 本週已發佈" if episode_path.exists()
        else ""
    )

    print(f"📊 {week} 候選新聞(依本週提及次數排序)")
    if week_status:
        print(f"   {week_status}\n")
    else:
        print()
    print(f"{'#':>3}  {'Score':>5}  {'Hits':>4}  {'Events':>6}  {'Links':>5}  Slug — Summary")
    print("─" * 110)

    for i, e in enumerate(entries[:8], 1):
        print(
            f"{i:>3}  {e['score']:>5}  {e['hits']:>4}  {e['events']:>6}  {e['related']:>5}  "
            f"{e['slug']} — {e['summary']}"
        )

    print(f"\n共 {len(entries)} 個 entity 本週被提到,顯示 top 8。")
    print(f"\n下一步:挑 3-5 個 slug,執行:")
    print(f"  uv run python3 cli.py research {week} slug1,slug2,slug3")


def cmd_research(week: str, slugs_csv: str):
    """讀 wiki page + related + 本週 raw,產 research notes 到 data/<week>/。"""
    slugs = [s.strip() for s in slugs_csv.split(",") if s.strip()]
    if not slugs:
        print("❌ 需要至少一個 slug")
        sys.exit(1)

    week_data = DATA / week
    week_data.mkdir(parents=True, exist_ok=True)

    # Cache this week's raw reports once
    raws = raw_paths_for_week(week)
    raw_texts = {p: p.read_text(encoding="utf-8") for p in raws}

    results = []
    for slug in slugs:
        wiki_page = WIKI_ROOT / "wiki" / f"{slug}.md"
        if not wiki_page.exists():
            print(f"⚠️  Wiki page 不存在:{slug}(跳過)")
            continue

        content = wiki_page.read_text(encoding="utf-8")
        lines = [
            f"# Research Notes: {slug} (week {week})",
            f"\n> Generated: {datetime.now().isoformat()}",
            f"\n## Primary Entity: {slug}\n",
            content,
        ]

        # Related entities
        related_section = content.split("## Related")[-1] if "## Related" in content else ""
        related_slugs = re.findall(r"\[\[([^\]\|]+?)(?:\|[^\]]+)?\]\]", related_section)
        related_slugs = [s for s in related_slugs if not s.startswith("raw/")]
        related_slugs = [s.replace("wiki/", "") for s in related_slugs]

        if related_slugs:
            lines.append(f"\n## Related Entities ({len(related_slugs)})\n")
            for rs in related_slugs:
                rpath = WIKI_ROOT / "wiki" / f"{rs}.md"
                if rpath.exists():
                    lines.append(f"\n### {rs}\n")
                    lines.append(rpath.read_text(encoding="utf-8"))

        # This week's raw snippets that mention this slug
        week_mentions = []
        for p, text in raw_texts.items():
            if re.search(rf"\[\[wiki/{re.escape(slug)}(?:\||\])", text):
                week_mentions.append((p, text))
        if week_mentions:
            lines.append(f"\n## 本週日報中的提及 ({len(week_mentions)} 篇)\n")
            for p, text in week_mentions:
                lines.append(f"\n### {p.relative_to(WIKI_ROOT)}\n")
                lines.append(text)

        out_path = week_data / f"{slug}.md"
        out_path.write_text("\n".join(lines), encoding="utf-8")
        total_chars = sum(len(l) for l in lines)
        results.append((slug, out_path, total_chars, len(related_slugs), len(week_mentions)))

    if not results:
        print("❌ 沒有任何 slug 產出 research notes")
        sys.exit(1)

    print(f"\n✅ 產出 {len(results)} 份 research notes 到 {week_data.relative_to(ROOT)}/\n")
    for slug, path, chars, rel, weekref in results:
        print(f"   {slug}: {chars:,} chars | related={rel} | 本週提及={weekref} 篇")
    print(f"\n下一步:Claude 讀 research + prompts/ → 寫 drafts/{week}.md")
    print(f"  uv run python3 cli.py draft {week} {slugs_csv}")


def cmd_draft(week: str, slugs_csv: str):
    """檢查 research 是否齊,提示 Claude 用 Write 工具存 draft。"""
    slugs = [s.strip() for s in slugs_csv.split(",") if s.strip()]
    week_data = DATA / week
    draft_path = DRAFTS / f"{week}.md"

    missing = [s for s in slugs if not (week_data / f"{s}.md").exists()]
    if missing:
        print(f"⚠️  這些 slug 沒有 research notes:{', '.join(missing)}")
        print(f"   請先:uv run python3 cli.py research {week} {slugs_csv}")
        sys.exit(1)

    if draft_path.exists():
        size = len(draft_path.read_text(encoding="utf-8"))
        print(f"📝 Draft 已存在:{draft_path.relative_to(ROOT)} ({size:,} chars)")
        print("   Claude 可以覆寫,或使用者確認後進 publish。")
        return

    print(f"📄 Draft 路徑就緒:{draft_path.relative_to(ROOT)}")
    print(f"   本週 slugs ({len(slugs)} 則):{', '.join(slugs)}")
    print(f"   Research notes:{week_data.relative_to(ROOT)}/")
    print()
    print("   Claude 應該:")
    print("   1. 讀 prompts/format.md + prompts/tone.md + prompts/quality.md")
    for s in slugs:
        print(f"   2. 讀 {week_data.relative_to(ROOT)}/{s}.md")
    print(f"   3. 先產大綱(hook + 每則要點 + transition + 結尾)給使用者確認")
    print(f"   4. 使用者點頭後,用 Write 工具存逐字稿到 {draft_path.relative_to(ROOT)}")
    print(f"   5. 跑 prompts/quality.md checklist 自檢,不過關就改")


def cmd_publish(week: str):
    """把 drafts/<week>.md 移到 episodes/ + git commit + push。"""
    draft_path = DRAFTS / f"{week}.md"
    if not draft_path.exists():
        print(f"❌ Draft 不存在:{draft_path.relative_to(ROOT)}")
        sys.exit(1)

    episode_path = EPISODES / f"{week}.md"
    shutil.move(str(draft_path), str(episode_path))

    # Move research notes too (so the episode has self-contained context)
    week_data = DATA / week
    episode_research_dir = EPISODES / f"{week}-research"
    if week_data.exists() and any(week_data.iterdir()):
        if episode_research_dir.exists():
            shutil.rmtree(episode_research_dir)
        shutil.copytree(week_data, episode_research_dir)

    chars = len(episode_path.read_text(encoding="utf-8"))
    print(f"✅ 已發佈:{episode_path.relative_to(ROOT)} ({chars:,} chars)")

    os.chdir(ROOT)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-m", f"episode: {week}"], check=True)
    result = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Git push 完成")
    else:
        print(f"⚠️  Git push 失敗:{result.stderr}")
        print("   可能需要手動 push。")


def cmd_status():
    """列 drafts / episodes / 本週 raw 狀態。"""
    print("📊 BOBA 週報進度\n")

    # Current week raw coverage
    cw = current_week()
    raws = raw_paths_for_week(cw)
    print(f"本週 ({cw}):{len(raws)}/7 篇日報")

    drafts = sorted(DRAFTS.glob("*.md"))
    if drafts:
        print("\n📝 Drafts:")
        for f in drafts:
            size = len(f.read_text(encoding="utf-8"))
            print(f"   {f.stem}: {size:,} chars")
    else:
        print("\n📝 Drafts: (無)")

    episodes = sorted(EPISODES.glob("*.md"))
    if episodes:
        print(f"\n✅ Episodes ({len(episodes)}):")
        for f in episodes:
            size = len(f.read_text(encoding="utf-8"))
            print(f"   {f.stem}: {size:,} chars")
    else:
        print("\n✅ Episodes: (無)")


# ────────────────────────── Entry point ──────────────────────────

def main():
    if len(sys.argv) < 2:
        print("BOBA 週報 CLI\n")
        print("用法:")
        print("  uv run python3 cli.py candidates [week]              # 列本週候選新聞 top 8")
        print("  uv run python3 cli.py research <week> <slug1,slug2>  # 產 research notes")
        print("  uv run python3 cli.py draft <week> <slug1,slug2>     # 準備 draft(Claude 寫)")
        print("  uv run python3 cli.py publish <week>                 # 發佈到 episodes/ + push")
        print("  uv run python3 cli.py status                         # 查進度")
        print(f"\n本週:{current_week()}")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "candidates":
        week = sys.argv[2] if len(sys.argv) > 2 else current_week()
        cmd_candidates(week)
    elif cmd == "research":
        if len(sys.argv) < 4:
            print("❌ 用法:uv run python3 cli.py research <week> <slug1,slug2,...>")
            sys.exit(1)
        cmd_research(sys.argv[2], sys.argv[3])
    elif cmd == "draft":
        if len(sys.argv) < 4:
            print("❌ 用法:uv run python3 cli.py draft <week> <slug1,slug2,...>")
            sys.exit(1)
        cmd_draft(sys.argv[2], sys.argv[3])
    elif cmd == "publish":
        if len(sys.argv) < 3:
            print("❌ 用法:uv run python3 cli.py publish <week>")
            sys.exit(1)
        cmd_publish(sys.argv[2])
    elif cmd == "status":
        cmd_status()
    else:
        print(f"❌ 未知指令:{cmd}")
        print("可用:candidates, research, draft, publish, status")
        sys.exit(1)


if __name__ == "__main__":
    main()

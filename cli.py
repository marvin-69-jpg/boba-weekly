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
    """掃 wiki entity 的 Key Events,找本週有事發生的 entity 作為候選新聞。"""
    dates = week_dates(week)
    date_strs = {d.strftime("%Y-%m-%d") for d in dates}

    wiki_dir = WIKI_ROOT / "wiki"
    if not wiki_dir.exists():
        print(f"❌ wiki 目錄不存在:{wiki_dir}")
        sys.exit(1)

    entries = []
    for wiki_page in wiki_dir.glob("*.md"):
        content = wiki_page.read_text(encoding="utf-8")
        # Find Key Events with dates falling inside this week
        this_week_dates = [
            m.group(1)
            for m in re.finditer(r"\*\*(\d{4}-\d{2}-\d{2})\*\*", content)
            if m.group(1) in date_strs
        ]
        if not this_week_dates:
            continue

        slug = wiki_page.stem
        # Summary = first non-heading non-frontmatter non-empty line
        summary = ""
        in_frontmatter = False
        for line in content.splitlines():
            s = line.strip()
            if s == "---":
                in_frontmatter = not in_frontmatter
                continue
            if in_frontmatter or not s or s.startswith("#"):
                continue
            summary = s[:80]
            break

        total_events = len(re.findall(r"\*\*\d{4}-\d{2}-\d{2}\*\*", content))
        related_section = content.split("## Related")[-1] if "## Related" in content else ""
        related = len(re.findall(r"\[\[", related_section))

        # Most recent event date within the week
        last_event = max(this_week_dates) if this_week_dates else ""

        entries.append({
            "slug": slug,
            "this_week": len(this_week_dates),
            "summary": summary or "(無摘要)",
            "total_events": total_events,
            "related": related,
            "last_event": last_event,
            # Score: this-week event count dominates; total depth is tiebreaker
            "score": len(this_week_dates) * 10 + total_events + related,
        })

    if not entries:
        print(f"❌ 本週 ({week}) 沒有任何 wiki entity 的 Key Events")
        print(f"   可能本週 boba-wiki 還沒 ingest,先跑 wiki 的 ingest.sh")
        sys.exit(1)

    entries.sort(key=lambda e: (e["score"], e["last_event"]), reverse=True)

    draft_path = DRAFTS / f"{week}.md"
    episode_path = EPISODES / f"{week}.md"
    week_status = (
        "📝 本週已有草稿" if draft_path.exists()
        else "✅ 本週已發佈" if episode_path.exists()
        else ""
    )

    raws = raw_paths_for_week(week)
    print(f"📊 {week} 候選新聞(wiki 本週有更新的 entity)")
    print(f"   掃描範圍:{dates[0]} ~ {dates[-1]}(ISO week {week}),raw 日報 {len(raws)}/7 篇")
    if week_status:
        print(f"   {week_status}")
    print()
    print(f"{'#':>3}  {'Score':>5}  {'本週事件':>8}  {'總事件':>6}  {'Links':>5}  最新  Slug — Summary")
    print("─" * 120)

    for i, e in enumerate(entries[:8], 1):
        print(
            f"{i:>3}  {e['score']:>5}  {e['this_week']:>8}  {e['total_events']:>6}  "
            f"{e['related']:>5}  {e['last_event'][-5:]:>5}  {e['slug']} — {e['summary']}"
        )

    print(f"\n共 {len(entries)} 個 entity 本週有事,顯示 top 8。")
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

        out_path = week_data / f"{slug}.md"
        out_path.write_text("\n".join(lines), encoding="utf-8")
        total_chars = sum(len(l) for l in lines)
        results.append((slug, out_path, total_chars, len(related_slugs)))

    # Also dump the whole week's raw reports once, shared across slugs
    if raw_texts:
        shared_raw = week_data / "_raw_week.md"
        raw_lines = [f"# Week {week} Raw Daily Reports\n"]
        for p in sorted(raw_texts):
            raw_lines.append(f"\n## {p.relative_to(WIKI_ROOT)}\n")
            raw_lines.append(raw_texts[p])
        shared_raw.write_text("\n".join(raw_lines), encoding="utf-8")

    if not results:
        print("❌ 沒有任何 slug 產出 research notes")
        sys.exit(1)

    print(f"\n✅ 產出 {len(results)} 份 research notes 到 {week_data.relative_to(ROOT)}/\n")
    for slug, path, chars, rel in results:
        print(f"   {slug}: {chars:,} chars | related={rel}")
    if raw_texts:
        shared_raw = week_data / "_raw_week.md"
        print(f"   _raw_week.md: 本週 {len(raw_texts)} 篇日報全文({shared_raw.stat().st_size:,} bytes)")
    print(f"\n下一步:Claude 讀 research + _raw_week.md + prompts/ → 寫 drafts/{week}.md")
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

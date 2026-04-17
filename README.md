# boba-weekly

BOBA 週報 — 從 [boba-wiki](https://github.com/marvin-69-jpg/boba-wiki) 撈本週最熱的 3-5 則新聞,產出 5-8 分鐘 YouTube 影片口播逐字稿(1500-2500 中文字)。

## Pipeline

```
candidates →(手動挑 3-5 則)→ research → draft → publish
```

## Quickstart

```bash
# 看本週候選新聞 top 8
uv run python3 cli.py candidates

# 挑好後做研究 + 產 draft(Claude 寫)
uv run python3 cli.py research 2026-16 openai-chip-deal,bitcoin-selloff,google-gemini
uv run python3 cli.py draft 2026-16 openai-chip-deal,bitcoin-selloff,google-gemini
# → Claude 讀 prompts/ + research,寫 drafts/2026-16.md

# 發佈
uv run python3 cli.py publish 2026-16
```

## 撰稿規範

- `prompts/format.md` — 逐字稿結構:Hook / 菜單 / 3-5 則新聞 / 結尾
- `prompts/tone.md` — BOBA 語氣 + YouTube 口播感
- `prompts/quality.md` — 品質自檢清單

## 前提

- Python 3.12 + [uv](https://github.com/astral-sh/uv)
- `/home/node/boba-wiki/` 已 clone 且最新

## 目錄

- `data/<week>/<slug>.md` — 每週 research notes(git-tracked)
- `drafts/<week>.md` — WIP 初稿(gitignored)
- `episodes/<week>.md` — 已發佈逐字稿 + 自帶 `<week>-research/`

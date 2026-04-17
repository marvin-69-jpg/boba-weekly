# boba-weekly

BOBA 週報 — YouTube 影片逐字稿產出工具。從 `boba-wiki` 挑本週最熱的 3-5 則新聞,寫成 5-8 分鐘口播逐字稿(1500-2500 字)。

---

## 指令格式

```bash
uv run python3 cli.py candidates [week]              # 列本週候選新聞 top 8
uv run python3 cli.py research <week> <slug1,slug2>  # 產 research notes
uv run python3 cli.py draft <week> <slug1,slug2>     # 準備 draft(Claude 寫)
uv run python3 cli.py publish <week>                 # 發佈到 episodes/ + push
uv run python3 cli.py status                         # 查進度
```

`week` 格式是 ISO week `YYYY-WW`(例:`2026-16`)。`candidates` 不給 week 時預設當週。

---

## Pipeline(混合選題流程)

```
candidates →(使用者挑 3-5 則)→ research → draft → (Claude 寫) → publish
```

1. **candidates**:掃本週 `boba-wiki/raw/YYYY/MM/DD.md` 七篇,抽出最常被提及的 wiki entity,score 排序列 top 8
2. **使用者在 Discord 挑 3-5 個 slug**(混合選題的人工部分)
3. **research**:讀每個 slug 的 wiki page + related + 本週 raw 提及,整合存到 `data/<week>/<slug>.md`
4. **draft**:檢查 research 齊了,提示 Claude 用 Write 工具寫逐字稿
5. Claude 讀 `prompts/format.md + tone.md + quality.md` + research,**先產大綱給使用者確認**,通過後寫初稿
6. **quality checklist** 自檢,不過關就改,最多 2 次
7. **publish**:移到 `episodes/<week>.md` + git commit + push

---

## 撰稿規範

| 檔案 | 用途 |
|---|---|
| `prompts/format.md` | 逐字稿結構(Hook → 菜單 → 3-5 則新聞 → 結尾),長度規範 |
| `prompts/tone.md` | BOBA 語氣 + YouTube 口播感 + 禁用語 |
| `prompts/quality.md` | 交稿前品質自檢清單 |

---

## 目錄結構

```
boba-weekly/
├── cli.py              ← 主入口
├── pyproject.toml      ← uv 管理
├── prompts/            ← 撰稿規範
│   ├── format.md
│   ├── tone.md
│   └── quality.md
├── data/<week>/        ← research notes(git-tracked,可回溯)
│   └── <slug>.md
├── drafts/             ← WIP 初稿(.gitignore)
│   └── <week>.md
└── episodes/           ← 已發佈
    ├── <week>.md
    └── <week>-research/
        └── <slug>.md
```

---

## 跨 Repo 依賴

- `/home/node/boba-wiki/` — 唯讀,用於選題和研究素材
  - `raw/YYYY/MM/DD.md` — 日報原稿(candidates 在這挑)
  - `wiki/<slug>.md` — entity page(research 讀這個)

**前提**:pod 內 `/home/node/boba-wiki/` 必須是最新的。不是的話先 `cd /home/node/boba-wiki && git pull`。

---

## 重要約束

- **逐字稿長度**:1500-2500 中文字(不含標點)
- **新聞則數**:3-5 則(少了太短,多了每則篇幅不夠)
- **每則新聞**:至少 2 個具體數字 + 標來源
- **口播感**:大聲唸一遍不卡舌、單句不超過 2 個逗號
- **不給明確投資建議**(「應該買」「建議賣」都不行)
- **用 Write 工具存初稿**,不要 bash heredoc
- **不要把 research notes 貼回 Discord**(太長),在 Discord 回 summary + draft link

---

## 典型的 Discord 對話

```
使用者:跑 2026-16 候選
Bot:[執行 candidates]  
    📊 2026-16 候選新聞(top 8):
    1. openai-chip-deal — 跟博通簽 1000 億晶片訂單
    2. bitcoin-selloff  — 跌破 9 萬美金...
    ...
    你想挑哪幾則?

使用者:1, 2, 5

Bot:[執行 research 2026-16 openai-chip-deal,bitcoin-selloff,<slug5>]
    [讀 prompts + research]
    大綱:
    - Hook:OpenAI 那筆 1000 億訂單
    - 菜單:OpenAI / Bitcoin / <第三則>
    - 第一則 OpenAI:重點在硬體綁定...
    - 第二則 Bitcoin:連到 AI 估值懷疑...
    - 第三則:...
    - 結尾:這三件事串起來看...
    大綱可以嗎?

使用者:可以

Bot:[Write drafts/2026-16.md,跑 quality checklist]
    已存 drafts/2026-16.md(1842 字)
    quality 自檢全部通過
    要我 publish 嗎?

使用者:發

Bot:[執行 publish 2026-16]
    已移到 episodes/2026-16.md,git push 完成
    GitHub:https://github.com/marvin-69-jpg/boba-weekly/blob/main/episodes/2026-16.md
```

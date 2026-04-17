---
name: boba-weekly
description: BOBA 週報 YouTube 逐字稿 + 投影片配圖製作 skill。受眾是加密新手散戶。
---

# BOBA 週報 Skill

每週一集 5-8 分鐘 YouTube 影片。從 `boba-wiki` 挑 **3 個大主題**（不是 3 則新聞）寫成 10 張投影片口播逐字稿，給加密新手散戶看。

SKILL.md 只放流程骨幹 + 規則索引。規則細節去讀對應的 feedback memory 或子文件。

---

## Pipeline

```bash
uv run python3 cli.py candidates [week]
uv run python3 cli.py research <week> <slug1,slug2,slug3>
uv run python3 cli.py draft <week> <slug1,slug2,slug3>
uv run python3 cli.py publish <week>
# 配圖另外寫 drafts/<week>-images.md
```

跨 repo 依賴：`/home/node/boba-wiki/`（唯讀）。開工前先 `cd /home/node/boba-wiki && git pull`。

撰稿規範：`prompts/format.md`（結構長度）、`prompts/tone.md`（語氣禁用語）、`prompts/quality.md`（交稿檢核）。

---

## 發佈 markdown 層級（硬規定）

```markdown
# 集名 / 一句話總結
## Hook
### Hook 投影片標題
內文
———
## 主題一：[大主題，用敘事標題]
### 投影片 A 標題
### 投影片 B 標題
———
## 主題二：[大主題]
### ...
———
## 主題三：[大主題]
### ...
———
## 結尾
### 結尾投影片標題
```

- H1 集名、H2 共 5 個（Hook + 3 主題 + 結尾）、H3 每張投影片
- 主題 H2 用人話敘事標題（不是「主題一」機械結構詞）
- `———` 只在 H2 之間當視覺分隔、不取代 H2

👉 `feedback_weekly_episode_topic_headings`

---

## 撰稿規則索引（規則細節去讀對應 memory）

### 主題與選題
- `feedback_weekly_three_topics_total` — 只有 3 個主題，投影片張數 ≠ 主題數
- `feedback_weekly_fewer_deeper` — 寧可少一主題講深
- `project_weekly_audience` — 受眾是新手散戶
- `feedback_weekly_continuity` — 延續上集敘事、不重講素材
- `feedback_weekly_verify_week_timeline` — 本週 raw 逐日驗證
- `feedback_weekly_use_bobacli_for_latebreaking` — 盤中事件用 `cli.py fetch`

### 格式
- `feedback_weekly_slide_format` — 每段=一張投影片 150-250 字
- `feedback_weekly_no_section_numbers` — 標題不用結構編號
- `feedback_weekly_title_narrative` — 標題有敘事質地
- `feedback_weekly_narrative_texture` — 內文有敘事質地
- `feedback_weekly_takeaway_per_slide` — 每張 slide 要有 takeaway

### 口播與語氣
- `feedback_weekly_conversational_tone` — 朋友聊天但沉穩
- `feedback_weekly_hook_no_metaphor` — Hook 直接丟事件+數字
- `feedback_weekly_chinese_firm_names` — 嘉信/貝萊德/高盛中譯，加密原生英文
- `prompts/tone.md` — 禁用語表 + 口播節奏

### 深度
- `feedback_weekly_mechanism_over_facts` — 寫機制不列基本新聞
- `feedback_weekly_explanation_depth` — 名詞解釋要有肉
- `feedback_weekly_learn_something` — 深挖到散戶學到東西就夠
- `feedback_weekly_no_reintroduction` — 已知概念一句話帶過

### 風格四大砍
- `feedback_weekly_no_drama_hype` — 不要戲劇性廢話
- `feedback_weekly_no_philosophical_closing` — 不要哲理格言結尾
- `feedback_weekly_no_preamble` — 不要元敘述鋪墊
- `feedback_weekly_show_dont_teach` — 用事實講故事不教學
- `feedback_weekly_humor_in_contrast` — 人物反差可輕微戲謔

---

## 配圖規則

- `feedback_weekly_image_style` — **象徵式漫畫彩蛋風**（榨汁機、展示櫃、三聯畫）
- 禁 Pepe、禁 🧋、禁動物代替真人、禁純數據當主視覺、禁 editorial 寫實照片風
- 真實人物漫畫化本人（Saylor 光頭+西裝、孫哥背心+笑容、川普金髮+紅領帶）

配圖文檔另存 `drafts/<week>-images.md`，每張 slide 一個梗 + 必要數字標註。

---

## Quality 自檢清單

交稿前大聲唸一遍（`prompts/tone.md` §自我檢核）並勾選：

- [ ] 只有 3 個主題、沒散成 4-5 則
- [ ] 每張 slide 有 takeaway、不是純事件
- [ ] 沒有「散戶要學的是」「這告訴我們」教學句
- [ ] 沒有哲理感想結尾
- [ ] 沒有戲劇性廢話（「群組喊完蛋」「發一條推特」）
- [ ] 沒有元敘述鋪墊（「先鋪墊」「先交代」）
- [ ] 已知概念（STRC/ATM/mNAV）沒有重新整段介紹
- [ ] 人物用**形容詞 + 人名**切入
- [ ] 傳統金融中譯名、加密原生英文
- [ ] 每個事件/數字對本週 raw 驗證過
- [ ] Hook 直接丟事件+數字、沒用抽象比喻
- [ ] 標題沒有「新聞一/Hook/菜單」結構詞、有敘事質地
- [ ] 發佈 markdown 有 5 個 H2（Hook + 3 主題 + 結尾）

---

## 檢討日誌

每集製作踩到的坑寫進 `retrospectives/YYYY-WW.md`，**不要塞進 SKILL.md**。

- `retrospectives/2026-16.md` — 第一次系統化產出，踩了 7 個坑（配圖三版反覆、戲劇廢話、哲理結尾、已知概念重講、元敘述鋪墊、Google 搜盤中事件、episodes 缺主題層）

# 音樂教材

樂理、作曲與配器教材的繁體中文翻譯與英文對照。

**[開啟閱讀網站](https://musiclord.github.io/music-textbooks-zh/)**

## 收錄教材

- **Open Music Theory Version 2**：基礎樂理、對位、和聲、曲式、爵士、流行音樂、十二音與配器。
- **《配器法原理》**（Nikolay Rimsky-Korsakov）：第一卷正文與第二卷譜例，保留章節及譜例的交互引用。

閱讀時以繁體中文為主，可逐節展開英文。提供全文搜尋、字級及深淺色調整、圖片放大與可切換的連續閱讀。外部資源以 ↗ 標示，另開分頁。

## 版本與授權

這是獨立翻譯與整理計畫，與原作者及出版社沒有官方隸屬或背書關係。翻譯使用 AI 協助並持續校訂，尚未經音樂教育專業人士完整審校。部分譜例與互動練習需至原來源查看，缺漏會在閱讀位置標示。

OMT 正文及適用的繁中翻譯採 **CC BY-SA 4.0**；個別素材保留原有授權。《配器法原理》使用 Project Gutenberg #33900 收錄的歷史公眾領域底本。尚未確認再發布權的圖像、外部總譜及相關演奏說明譯文以原來源連結提供。

詳見 [來源、授權與版本說明](https://musiclord.github.io/music-textbooks-zh/licenses.html)、[LICENSE.md](LICENSE.md) 及 [公開版素材清單](docs/publication-manifest.json)。

## 發布與更新

`docs/` 是可直接託管的完整靜態網站。GitHub Actions 會檢查頁面、內部連結、搜尋定位與素材排除結果，再發布到 GitHub Pages。線上閱讀不需要維持本機電腦或 Python 服務開啟。

本儲存庫保存公開閱讀版本與發布檢查程式。維護者的本機稿本、來源快照、工具及工作紀錄留在本機工作目錄。

維護者從本機稿本重建後，執行：

```powershell
.\readings.ps1 build
.\.tools\venv\Scripts\python.exe -X utf8 scripts\prepare_publication.py
```

檢查公開版本（只需要 Python 3.10+ 與 lxml 6.0.2）：

```sh
python scripts/prepare_publication.py --verify
```

確認變更後提交並推送 `main`，網站就會自動更新。重新準備公開版不會修改本機閱讀版；新增的限制授權聲明會要求先更新 `publication-policy.json`。

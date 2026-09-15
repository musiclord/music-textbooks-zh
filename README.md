# 音樂教材

**非營利教育分享・程式碼開源・繁體中文與英文對照**

免費閱讀樂理與配器教材，支援全文搜尋、圖片放大、字級調整及連續閱讀。

**[進入閱讀網站](https://musiclord.github.io/music-textbooks-zh/)** · [版權與授權](COPYRIGHT.md) · [回報問題](https://github.com/musiclord/music-textbooks-zh/issues)

## 收錄教材

- **[Open Music Theory Version 2](https://musiclord.github.io/music-textbooks-zh/omt/)**：基礎樂理、對位、和聲、曲式、爵士、流行音樂與配器。
- **[《配器法原理》](https://musiclord.github.io/music-textbooks-zh/rk/)**：Nikolay Rimsky-Korsakov 著，收錄第一卷正文與第二卷譜例。

## 授權

| 範圍 | 授權 |
| --- | --- |
| 本站閱讀介面與發布程式 | [MIT](LICENSE) |
| OMT 適用正文、本站繁中翻譯及獨立譯註 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| 《配器法原理》歷史英文底本 | 公眾領域，詳見 [版權說明](COPYRIGHT.md) |
| 第三方圖片、譜例與程式元件 | 依個別授權及原作者署名 |

本站以非營利方式提供閱讀；MIT 與 CC BY-SA 4.0 的使用權不因此縮減。部分素材採 CC BY-NC-SA，另有非商業限制。

本網站為獨立翻譯整理計畫，非原作者或出版社的官方中文版本。譯文持續校訂；部分譜例及互動練習由原來源提供。

## 本機預覽與貢獻

網站檔案位於 `docs/`，可直接修改後預覽：

```sh
python -m http.server 8000 --directory docs
```

歡迎透過 Issues 或 Pull Request 修正譯文、排版及來源標示。推送至 `main` 後，GitHub Actions 會檢查並發布網站。

# LaTeX + Zotero + Overleaf 工作流指南

## 项目文件清单

```
latex_project/
├── main.tex          ← 主文档（已转换全部章节内容）
├── references.bib    ← BibTeX 参考文献（需用 Zotero 补全）
└── figures/          ← 图片文件夹（需从 Word 中导出图片放入）
```

---

## 第一步：修复参考文献（Zotero）

你的 Word 稿中 references 有几类问题：

| 问题类型 | 涉及条目 | 解决方式 |
|---------|----------|---------|
| 缺少 DOI / volume / pages | BagheriEsfeh2025, Hou2024, Mulville2016, Shirzadi2025, Westermann2021 | Zotero 自动抓取 |
| 信息不完整（标注 TODO） | JiangKazmi2024, Sheridan2022, TaylorSymonds | 手动查找补全 |
| Piddington2020 vs BRETrust2020 可能重复 | 两者标题相同，作者不同 | 确认是否为同一份报告 |
| 作者名拼写需确认 | Sheridan 被标记（C. Sheridan vs Charles） | 统一 |

### 操作步骤

1. **打开 Zotero → 创建新 Collection**：命名为 `Dissertation_BENV0165`

2. **用 DOI 批量导入已知条目**：
   - 点击 Zotero 工具栏的 "Add Item by Identifier"（魔术棒图标）
   - 逐个粘贴已知 DOI（如 `10.1016/j.enbuild.2021.111586`）
   - Zotero 会自动填充完整元数据

3. **手动补全 TODO 条目**：
   - `JiangKazmi2024`：搜索 "Jiang Kazmi causal overheating" 在 Scopus/Google Scholar
   - `Sheridan2022`：搜索 "Sheridan Botti automated building measurement"
   - `TaylorSymonds`：搜索 "Taylor Symonds indoor overheating converted lofts London"
   - 找到后用 Zotero Connector 直接从浏览器抓取

4. **检查每条记录**：确保 author, year, title, journal/booktitle, volume, pages, DOI 字段完整

5. **导出 BibTeX**：
   - 右键 Collection → Export Collection → 格式选 **Better BibTeX**（需安装 Better BibTeX 插件）
   - 勾选 "Keep updated"（自动同步）
   - 保存为 `references.bib`，覆盖项目中的初始版本

### Better BibTeX 插件（强烈推荐）

安装地址：https://retorque.re/zotero-better-bibtex/

好处：
- 自动生成稳定的 citation key（如 `Lawrence2021`）
- 可自定义 key 格式：`[auth][year]` 与你 .tex 中的 `\citep{Lawrence2021}` 一致
- 自动导出 + 实时同步到 Overleaf

**设置 citation key 格式**：Zotero → Preferences → Better BibTeX → Citation Keys → 设置为：
```
[auth][year]
```

---

## 第二步：上传到 Overleaf

### 方案 A：手动上传（简单）

1. 登录 Overleaf → New Project → Upload Project
2. 将 `main.tex`、`references.bib`、`figures/` 文件夹打包为 zip 上传
3. 每次 Zotero 更新后重新导出 `references.bib` 并替换 Overleaf 中的版本

### 方案 B：Git 同步（推荐，需 Overleaf Premium）

1. Overleaf 项目 → Menu → Git → 复制 Git URL
2. 本地 clone：`git clone https://git.overleaf.com/your-project-id`
3. 将 `main.tex`、`references.bib`、`figures/` 复制进去
4. `git add . && git commit -m "init" && git push`
5. Zotero Better BibTeX 自动导出路径设为该 git repo 下的 `references.bib`
6. 每次文献更新后：`git add references.bib && git commit -m "update refs" && git push`

### 方案 C：Zotero + Overleaf 直连（最省事）

Overleaf 原生支持从 Zotero 同步 .bib 文件：
1. Overleaf → New File → From Zotero
2. 选择你的 Collection → 导入
3. 之后可在 Overleaf 中点击 "Refresh" 同步最新文献

---

## 第三步：导出 Word 中的图片

Word 中的图片需手动提取放入 `figures/` 文件夹：

1. 将 `dissertation_draft.docx` 重命名为 `.zip` → 解压
2. 图片在 `word/media/` 文件夹中
3. 重命名并复制到 `figures/`：

```
image1.png → figures/workflow.png
image2.png + image3.png → figures/3d_model.png（合并或选一张）
image4.png → figures/target_distributions.png
image5.png → figures/r2_comparison.png
image6.png → figures/parity_plots.png
image7.png → figures/loss_curves.png
image8.png → figures/shap_global.png
image9.png → figures/shap_beeswarm.png
image10.png → figures/rf_mdi.png
```

建议用 Python 脚本重新生成高分辨率 PDF 格式图表（LaTeX 中 PDF 比 PNG 清晰）。

---

## 第四步：编译检查

在 Overleaf 中：

1. 设置编译器：Menu → Compiler → **pdfLaTeX**
2. 主文档：Menu → Main document → `main.tex`
3. 点击 Recompile

### 可能遇到的问题

| 问题 | 解决方法 |
|------|---------|
| `agsm.bst` 找不到 | 改为 `\bibliographystyle{plainnat}` 或上传 `agsm.bst` |
| 引用显示 `[?]` | 运行两遍编译，或检查 citation key 是否匹配 |
| 图片找不到 | 确认 `figures/` 中文件名与 `\includegraphics` 一致 |
| 表格溢出页面 | 调整 `\footnotesize` 或用 `\resizebox` |

---

## 第五步：日常工作流

```
┌─────────────┐     导出 .bib      ┌──────────┐
│   Zotero    │ ──────────────────→ │ Overleaf │
│  管理文献    │  Better BibTeX     │  编辑 .tex │
└─────────────┘  自动/手动同步      └──────────┘
                                        ↑
┌─────────────┐     重新生成           │
│  Python     │ ──────────────────→  figures/
│  ML 脚本    │   高清 PDF 图表
└─────────────┘
```

### 每次修改的步骤

1. **新增文献**：Zotero 中添加 → 重新导出/同步 .bib → Overleaf 自动更新
2. **修改正文**：直接在 Overleaf 编辑 `main.tex`
3. **更新图表**：Python 重新生成 → 替换 `figures/` 中的文件
4. **检查引用**：编译后在 PDF 中确认所有 `\citep{}` 正确显示

---

## 需要你手动完成的事项清单

- [ ] 安装 Zotero Better BibTeX 插件
- [ ] 用 DOI/搜索补全所有标记 TODO 的文献条目
- [ ] 确认 Piddington2020 与 BRETrust2020 是否为同一报告
- [ ] 补全 Jiang & Kazmi (2024), Sheridan (2022), Taylor et al. 的完整出版信息
- [ ] 从 Word 文件提取图片到 `figures/` 文件夹
- [ ] 上传项目到 Overleaf 并测试编译
- [ ] 填写 Table 4.1 中缺失的 R² 和 MAE 数值
- [ ] 撰写 Discussion 和 Conclusion 章节
- [ ] 用 Python 脚本重新生成高分辨率 PDF 图表（可选但推荐）

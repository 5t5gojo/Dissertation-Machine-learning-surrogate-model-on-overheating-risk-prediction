# 会议论文

## 最新结果入口（2026-10-05）

当前结果采用 **corrected V2 建筑模型 + rounded C1 指标**。先读
[`09_rounded_training/2026-10-05_corrected_v2/reports/RESULTS_SUMMARY.md`](09_rounded_training/2026-10-05_corrected_v2/reports/RESULTS_SUMMARY.md)，
不要把下方历史 DSY1 报告或原始毕业论文模型分数当作当前结果。

- `06_model_sensitivity/2026-10-04_idf_audit/`：建筑模型修正的配对敏感性实验。
- `07_corrected_full/2026-10-04_combined_v2/`：两种天气、两种住宅共 8,000 个修正案例及未取整 C1 的历史评价。
- `08_metric_rounding/2026-10-05_corrected_v2/`：利用现有逐时输出核对 C1/C3 取整及同区联合标记，不重跑 EnergyPlus。
- `09_rounded_training/2026-10-05_corrected_v2/`：当前训练表、五次匹配划分、选参记录、预测、SHAP、置换重要性与评价报告。

本次 GitHub 同步保留实验脚本、派生 CSV、配置和核查记录；不发布正文、回复信、
原始逐时目录、逐例生成的 IDF、重复训练模型二进制文件或受许可限制的 CIBSE EPW。
这些文件仍保留在本地，没有删除。仓库中的完成记录描述原始本地运行，不能替代被排除的文件；
若要完整重跑或模型重载检查，需要恢复或重新生成相应依赖。脚本中保留的本地路径也需按环境调整。
`01_manuscript/` 仅为本地正文目录，不是 GitHub 下载入口。历史图表没有自动变成 rounded C1 版本。

## 历史 DSY update (2026-10-03，已被上述结果替代)

DSY1 simulation (4000 cases), independent audit, repeated model evaluation (180 candidates, five splits) and result verification are complete. Read `05_reviewer_feedback/DSY1_results_summary.md` first. New data are under `03_data/weather_scenarios/` and figures under `04_figures/Z1_DSY1_2030s_HIGH50_CIBSE_v1.1/`. The September no-DSY Word manuscript is preserved and still requires integration of these results; do not submit it as a DSY paper. See `DSY1_recovery_notes.md` in the feedback directory for the resolved aggregation fault.

以下记录描述最初无 DSY 的评审修订，保留用于追溯，不是当前论文或实验入口。

- `01_manuscript/original_submission/`：p129v1 原稿快照，保留未改动版本。
- `02_scripts/`：指标审计、重复评估、报告、Word 生成及验证脚本的共享源文件链接。
- `03_data/audit/`：4000 个案例的指标审计。
- `03_data/evaluation/`：180 次候选流程评估、重复划分、预测与特征重要性。
- `03_data/shared_simulation_results/` 和 `shared_lhs/`：共享原始数据入口，不复制数据。
- `04_figures/`：本轮修订的 PNG 和 PDF 图表。
- `05_reviewer_feedback/评审修改说明.md`：中文修改总结与未解决事项。
- `05_reviewer_feedback/response_to_reviewers.md`：英文逐条回复草稿。
- `05_reviewer_feedback/results_summary.md`：实验结果明细。

原脚本通过 formal model file/output/reviewer_revision 的兼容链接继续写入这些分类目录；不要在两个入口分别维护不同副本。两处指向同一批文件。

该早期阶段未包含 DSY；后续 DSY 与修正实验见上方版本入口。实测验证和因果实验仍未完成。

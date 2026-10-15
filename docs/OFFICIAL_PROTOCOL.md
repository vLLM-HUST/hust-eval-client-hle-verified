# 协议来源与差异

## 来源

- HLE-Verified
  数据：https://github.com/SKYLENAGE-AI/HLE-Verified/tree/b705e0fb541c025a1532ce0d60d70ae2f53b00e0
- 原版 HLE
  执行协议：https://github.com/centerforaisafety/hle/tree/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval
- 本项目 official_prompts.py 保存原始 Python 字符串值，SOURCE 记录原文件 SHA-256。
- 作答 SYSTEM_PROMPT、Judge JUDGE_PROMPT 从上述源码 AST 提取，未添加自定义判分指令。
- HLE-Verified 的 judge_round1/2 是数据修复/交叉审核；Three_Math_Solver_Text 是多模型重复解题诊断，不直接当作本客户端的标准单次评测入口。

## 保留的内容

作答使用 system 格式指令，user 包含题目文本和可选 image_url；要求 Explanation、Answer、Confidence。参考答案不进入作答请求。 Judge 使用原版单条
user 提示词，包含题目、原始回答、参考答案，不独立求解。与原版一样 Judge 不再附图。 Structured Outputs 使用 ExtractedAnswer
的五个字段：extracted_final_answer、reasoning、correct(yes/no)、confidence(integer)、strict(true)。 评分全部题型均走
Judge，不擅自把 multipleChoice 改为本地字母匹配。 准确率分母包含本次选中的全部题目；失败/无法判分单独记录，作为非成功计入分母，不能当作已确认答错。

## 明确的本地差异

- 原脚本默认 o3-mini-2025-01-31；本地示例 Qwen3.5-35B-A3B。单次试验。
- 原版 max_completion_tokens；本客户端用服务兼容的 max_tokens，实际值冻结。Judge 示例8192，原脚本4096。
- 示例固定 temperature=0/seed=17/thinking=false；默认并发1，c4/c16示例显式选择并发4/16，本次全量并发16。不能称为原论文模型配置。
- 原版 OpenAI SDK parse，本地直接发送等效 JSON schema 并验证原始 JSON。confidence 限制0..100，拒绝bool；重复键/非JSON/额外字段不被接受。
- 默认 strict_json 要求 Judge 正常 stop 且完整符合 schema。可显式选 complete_json：length 时仅完整 JSON 可恢复，记录审计标记；不能解析半截
  JSON或退回 VERDICT/yes正则。
- 作答 length 仍提交已有正文；每题记录 finish_reason。失败不会自动重试改变统计口径。
- 本项目不输出 calibration_error：固定上游函数漏掉末 bin 且 \<100 条时失败；保存 confidence 供后续明确版本的指标计算。
- bench 支持独立文本/图片性能测试；旧materialize仍只导出文本，bench-materialize从已封存结果导出两种模态。原题/真实图片保留，但无准确率system
  prompt；服务模板一次、thinking=false、temperature0、seed0、上限256、EOS允许。不能称为准确率请求重放。

Gold 为主报告、Revision 为单独补充报告；Uncertain 不默认混入。文本子集必须显式 --modality text-only，记录排除列表。

# 全量前待解决项

## 1. Qwen Judge 的结构化 JSON 空白循环（真实 smoke 已复现）

smoke 的 Gold 一题已经输出 extracted_final_answer/reasoning/correct/confidence，但在最后 strict 字段的冒号后不断生成制表符，达到8192 token。
严格 JSON 解析正确地将其标记 invalid_judge，没有把残缺 JSON 中出现的 correct 当成完整判决。

已审阅当前服务端安装源码：
- /vllm-workspace/vllm/vllm/sampling_params.py 定义了请求字段 disable_any_whitespace。
- v1/structured_output/backend_xgrammar.py 与 backend_guidance.py 实际读取的是服务级 structured_outputs_config.disable_any_whitespace。
- 因此不能仅向客户端请求添加同名字段并宣称已修复。

候选服务级配置（**未启动、未验证的新 profile**）：
```json
{"backend":"xgrammar","disable_any_whitespace":true}
```
对应 structured_outputs_config。需要操作者外部启动服务时配置；本客户端不启动服务、不改服务源码。
应新建 profile 和 fresh startup/effective receipt，重放失败样本并补充多题 Judge 验证；保留原始提示词和 response_format schema。
这只是候选修复，尚无开启该选项后的真实验证结果。

## 2. 长题的 Judge 上下文预算

当前 max_model_len=32768、solver max_tokens=16384、judge max_tokens=8192。
按原始题干、参考答案与固定 Judge 模板计算，以下 Revision 题在作答用满上限时可能超上下文：

| case_id | 不含作答/chat template 的 Judge 文本 token | 加两阶段上限后的估计 |
|---|---:|---:|
| revision-6720241e20239af7af582ae1 | 9910 | 34486 |
| revision-67228ecf93273f2ea4d39e3e | 10366 | 34942 |
| revision-672cba8ce9bdca604f9e0c12 | 13793 | 38369 |

这是规划上界估计，不代表这三题实际一定失败。图像展开与 chat template 还需单独计入。
选择更大的服务上下文，或明确较小的作答/Judge预算并固定 profile；不能静默截掉题目、参考答案或模型回答。
全量前需用真实请求 tokenization 再检查边界。

## 当前状态

远程客户端和基础功能验证已完成。没有启动1811题全量，没有提交成绩 PR。
本次四题专门选每个子集/模态中最短输入，只用于功能验证，不能外推模型准确率、截断比例或全量时长。

## 新 profile 验证中（2026-10-14）

`examples/profile.hle_ws64k.json` 提议上下文65536、xgrammar服务级空白限制。作答16384、Judge8192、并发1不变。客户端新增两个结构化输出字段的argv/startup日志核验；31项单元测试通过。服务由仓库外的操作者脚本启动。真实重放、全数据tokenization及补充小样本尚待完成；不能将配置存在视为修复已通过。

## 第二轮已验证事实（2026-10-14，补充小样本仍在执行）

新服务真实启动完成，客户端20项配置均由实际argv与startup日志核验通过，包括xgrammar和disable_any_whitespace=True。原始失败Judge请求保持不变，重放后stop正常结束，130个输出token、完整官方schema JSON；旧8192截断记录保留。单题成功不保证全量无截断。

全部1811题已通过服务端/tokenize预检，包含全部图片和实际chat template：最大solver输入16466，加16384输出预算为32850；Judge空回答模板token数加两阶段预算的最大投影38381。新max_model_len=65536覆盖上述预算。Judge投影不是实际生成回答重新分词后的精确上界；服务不会静默裁切输入，真实错误仍保留。

11题补充验证覆盖Gold/Revision、文字/图片、exactMatch/multipleChoice，并包含三道长题。只有全部solver请求成功且Judge完整JSON有效才允许顺序启动Gold668、Revision1143全量；solver length允许但单独统计。全量两份报告分别封存，不能合并当官方成绩。并发1、solver16384、judge8192，零自动重试，strict_json不变。

远程执行由仓库外campaign脚本编排，客户端不管理服务。项目只保存在本地和远程工作副本，未发布GitHub。

本轮目录：`/root/runs/hle-verified/hle-ws64k-campaign-20261014T063659Z`；状态见目录内 `STATUS`。编排日志：`/root/runs/hle-verified/campaign_ws64k.log`。此文档仅记录检查时状态，不代表全量已完成。

## 用户切换到并发4（2026-10-14）

并发1全量在Gold完成21条作答时停止，保留为未完成运行；不作为全量成绩。新的solver.c4.json和judge.c4.json均设concurrency=4，其他请求参数保持不变。沿用同一运行中的服务，Gold和Revision均用新计划从头运行，不混合旧结果。图文bench仍排在全部准确率测试完成后。最新运行目录由远程 `/root/runs/hle-verified/CURRENT_CAMPAIGN` 指向。

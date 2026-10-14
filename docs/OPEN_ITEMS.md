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

# hust-eval-client-hle-verified

面向已运行的 OpenAI-compatible 服务的独立 Python 客户端。**不启动、停止或配置 vLLM 服务。**

支持 HLE-Verified 数据冻结、原版 HLE 作答/Judge 提示词、图文请求、结构化 JSON 评分、断点续跑、逐题证据、文本 bench 输入、启动回执采集、模型小文件哈希及结果表 SHA-256 绑定。

## 评测范围

固定数据提交 `b705e0fb541c025a1532ce0d60d70ae2f53b00e0`：

| 子集 | 总数 | 文本 | 图片 |
|---|---:|---:|---:|
| Gold | 668 | 575 | 93 |
| Revision | 1143 | 1025 | 118 |

默认 Gold + Revision，分别统计；默认保留图片。Uncertain 仅显式选择，不进入默认主报告。
图片保留原始 data URL，图像数据包含在冻结文件哈希中。不会忽略图片退化为纯文本题。
采用数据中的最终 question/answer，不使用 original_question/original_answer 回退。参考答案仅发送给 Judge。

**这是原版 HLE 评分协议对 HLE-Verified 的适配，不是 Verified 作者审核/修复脚本的复现，也不是官方排行榜复现。**
示例模型和 Judge 均为 Qwen3.5-35B-A3B，temperature=0、seed=17、thinking=false、并发1；作答16384/Judge8192。
Judge 返回严格 JSON；默认 Judge 截断无效，作答截断仍将原始回答送 Judge。不是 FrontierScience 的 VERDICT 规则。

## 当前验证状态

30项测试通过；真实4题作答全部返回，Judge 3条有效、1条JSON空白循环截断；文本bench 2条成功。
**尚未启动全量。** 全量前需解决 Judge 空白循环并明确长题上下文预算，见 [OPEN_ITEMS.md](docs/OPEN_ITEMS.md)。

## 安装

需要 Python >=3.9；核心客户端无第三方依赖。bench 子命令另需客户端环境安装兼容的 vLLM。

```bash
cd /root/hust-eval-client-hle-verified
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/hust-eval-hle-verified --help
.venv/bin/python -m unittest discover -s tests -v
```

完整步骤见 [QUICKSTART.md](docs/QUICKSTART.md)，协议差异见 [OFFICIAL_PROTOCOL.md](docs/OFFICIAL_PROTOCOL.md)，证据要求见 [EVIDENCE.md](docs/EVIDENCE.md)。

## 子命令

- `fetch / inventory / prepare`：验证固定数据哈希、统计子集、冻结运行计划和源码。
- `run / judge / summary`：作答、结构化判分、逐题及分组报告；已完成请求在相同配置下可 resume，不自动重试失败请求。
- `materialize / bench`：**仅文本的性能探针**；不代表多模态准确率工作负载。
- `receipt / contract / hash-model / hash-file`：接收真实服务证据、模型文件清单与哈希。
- `seal evidence / table / seal final / seal check`：证据 → 结果表 → manifest 的非循环绑定。

代码和证据必须固定后再全量。修改任何核心模块后，旧 plan 拒绝继续执行；应使用归档源码或新建 plan。

图文压测及封存结果导入步骤见 [docs/BENCH.md](docs/BENCH.md)。

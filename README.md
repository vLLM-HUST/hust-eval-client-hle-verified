# hust-eval-client-hle-verified

[![Client tests](https://github.com/vLLM-HUST/hust-eval-client-hle-verified/actions/workflows/ci.yml/badge.svg)](https://github.com/vLLM-HUST/hust-eval-client-hle-verified/actions/workflows/ci.yml)

面向**已经运行的 OpenAI-compatible 服务**的独立 Python 评测客户端，支持 HLE-Verified 文本和图片题的作答、Judge
评分、图文性能压测和证据封存。**不启动、停止或配置 vLLM 服务。**

核心客户端无第三方运行依赖；`bench` 调用操作者另行安装的 `vllm bench serve`。 模型作答、Judge 与性能压测是独立步骤，准确率和吞吐不会混为同一个指标。

## 支持什么

- 固定数据版本与 SHA-256，保留原题文字和图片，冻结计划、提示词、配置与客户端源码。
- 使用原版 HLE 的作答/Judge 提示词和结构化 JSON schema；保留逐题请求、响应、usage、finish_reason。
- 独立设置 solver/Judge endpoint、模型、并发和输出预算；支持同一计划下的断点续跑。
- 按 Gold、Revision、模态和学科报告成绩；单独统计传输失败、未判定和截断。
- 分别执行文本、图片 `vllm bench serve`；图片请求发送真实图片，不退化为纯文本。
- 采集既有服务回执，核对实际 argv、startup log 与 profile；模型小文件哈希和权重清单。
- 将执行证据、结果表和 manifest 通过 SHA-256 关联并复验。

## 数据与评分口径

使用作者发布的
[HLE-Verified](https://github.com/SKYLENAGE-AI/HLE-Verified/tree/b705e0fb541c025a1532ce0d60d70ae2f53b00e0)，
固定提交 `b705e0fb541c025a1532ce0d60d70ae2f53b00e0`。这不是未经修改的原始 HLE 数据集。

| 子集      | 总数 | 文本 | 图片 | 默认运行       |
| --------- | ---: | ---: | ---: | -------------- |
| Gold      |  668 |  575 |   93 | 是，单独报告   |
| Revision  | 1143 | 1025 |  118 | 是，单独报告   |
| Uncertain |  689 |    — |    — | 否，须显式选择 |

采用数据中最终的 question/answer；参考答案只交给 Judge，不进入 solver 请求。 全部题型均由 Judge 判分，包括 multipleChoice，不擅自改为本地选项匹配。

默认 `strict_json` 要求 Judge 正常 `stop` 且返回符合 schema 的完整 JSON。 Judge
截断或无效时记为**未判定**，保留在全部选题的分母中，不等于已确认答错。 Solver 截断仍将已有回答交给 Judge，不直接判错；不自动重试、不解析半截 JSON。

本项目采用[原版 HLE 执行协议](https://github.com/centerforaisafety/hle/tree/22ed3074b1e7b134bcbc09028d0ba320839b0655/hle_eval)，
是对 HLE-Verified 的适配，**不是 Verified 作者数据审核/修复脚本的复现，也不是官方排行榜复现**。 示例由 Qwen3.5-35B-A3B 同时作答和代替官方
Judge。具体差异见 [评分协议](docs/OFFICIAL_PROTOCOL.md)。

## 安装

需要 Python >=3.9。可在容器内或能访问推理服务的另一台机器运行。

```bash
git clone https://github.com/vLLM-HUST/hust-eval-client-hle-verified.git
cd hust-eval-client-hle-verified
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
hust-eval-hle-verified --help
python -m unittest discover -s tests -v
```

开发时可改为 `python -m pip install -e .`。复现实验时先固定本仓库 commit， 再安装、冻结计划；不要一边运行一边修改源码。GitHub 发布不等于已发布 PyPI
包。

## 开始评测前准备

1. 可访问的模型服务；图片题要求图文输入支持，Judge 要求 JSON schema / Structured Outputs 支持。
1. 两份请求配置：修改 `base_url`、`model`、`model_artifact`、并发与预算。 有鉴权时将 `api_key_env`
   设为环境变量名，密钥只放环境变量，不写入配置或仓库。
1. 操作者提供实际服务 argv、真实启动日志与对应 profile；跨机器运行时需要先复制这些证据。 `hash-model` 读取的是客户端可见文件，不能仅凭远程模型路径推断权重一致。
1. 为每次运行使用新的输出目录；先验证文字、图片、Judge 和上下文预算，再做全量。

| 配置                                         | solver / Judge 并发 | 用途               |
| -------------------------------------------- | ------------------- | ------------------ |
| `examples/solver.json`、`judge.json`         | 1 / 1               | 保守的默认示例     |
| `examples/solver.c4.json`、`judge.c4.json`   | 4 / 4               | 显式并发 4         |
| `examples/solver.c16.json`、`judge.c16.json` | 16 / 16             | 本次全量使用的并发 |

上述示例均为 temperature=0、seed=17、thinking=false；solver 上限16384、Judge 上限8192。
并发和预算要适配实际服务；不保证不同并发下每题输出完全相同。 `examples/profile.hle_ws64k.json` 是本次65536上下文、xgrammar空白限制的参考配置，
**仅用于对照验证，不会修改或启动服务**；里面的 expected model revision 不代表本地权重已验证。

## 最短使用流程

以下演示 Gold；Revision 单独新建目录并将 `--subset gold` 改为 `--subset revision`。
全部服务证据路径须换成自己实际采集的文件。完整流程、smoke、续跑和封存见 [QUICKSTART](docs/QUICKSTART.md)。

```bash
HLE_ASSETS=/data/hle-verified
HLE_RUN=/data/runs/hle-gold-001

# 新目录执行一次；下载后校验固定数据字节及 SHA-256。
hust-eval-hle-verified fetch --output "$HLE_ASSETS"
hust-eval-hle-verified inventory --assets "$HLE_ASSETS"

mkdir -p "$HLE_RUN"
cp /path/to/actual-profile.json "$HLE_RUN/profile.json"
hust-eval-hle-verified receipt --run-dir "$HLE_RUN" \
  --base-url http://127.0.0.1:18180 --profile "$HLE_RUN/profile.json" \
  --startup-log /path/to/frozen-startup.log --server-argv /path/to/actual-argv.json
hust-eval-hle-verified contract --profile "$HLE_RUN/profile.json" \
  --out "$HLE_RUN/runtime-contract.json"
hust-eval-hle-verified hash-model --model /models/Qwen3.5-35B-A3B \
  --small-only --out "$HLE_RUN/model-small-before.json"

hust-eval-hle-verified prepare --assets "$HLE_ASSETS" --subset gold \
  --solver-config examples/solver.c16.json --judge-config examples/judge.c16.json \
  --solver-runtime-contract "$HLE_RUN/runtime-contract.json" \
  --judge-runtime-contract "$HLE_RUN/runtime-contract.json" --output "$HLE_RUN/plan"

# 先按 QUICKSTART 用独立输出目录验证文字、图片和 Judge，再执行以下全量步骤。
hust-eval-hle-verified run --plan "$HLE_RUN/plan" --output "$HLE_RUN/full/solver"
hust-eval-hle-verified judge --plan "$HLE_RUN/plan" \
  --responses "$HLE_RUN/full/solver" --output "$HLE_RUN/full/judge"
hust-eval-hle-verified summary --plan "$HLE_RUN/plan" \
  --responses "$HLE_RUN/full/solver" --grades "$HLE_RUN/full/judge" \
  --output "$HLE_RUN/full/report"
```

若 solver 与 Judge 使用不同服务，应分别采集回执并传入各自的 runtime contract。 只记录预期 profile 不等于拿到了实际 effective/startup
receipt；无法取得的字段必须保留为未知。

## 图文 bench

准确率结果封存后，使用 `bench-materialize` 从旧结果导出**独立的新压测输入**。 它验证原 seal 后读取不可变数据，不绕过旧 `load_plan`
的源码哈希检查，也不修改已封存目录。

```bash
HLE_BENCH=/data/runs/hle-bench-001
hust-eval-hle-verified bench-materialize --accuracy-run "$HLE_RUN" \
  --modality image --output "$HLE_BENCH/exports/gold-image"
hust-eval-hle-verified bench --run-dir "$HLE_BENCH/gold-image" --name gold-image \
  --dataset "$HLE_BENCH/exports/gold-image/prompts.jsonl" \
  --input-manifest "$HLE_BENCH/exports/gold-image/prompts.jsonl.manifest.json" \
  --modality image --base-url http://127.0.0.1:18180 --served-model qwen3.5-35b \
  --tokenizer /models/Qwen3.5-35B-A3B --num-prompts 93 --output-len 256
```

文本导出用 `--modality text --sample 200`，bench 对应 `--modality text --num-prompts 200`。 本次四组为
Gold文本200、Revision文本200、Gold图片93、Revision图片118，分别报告。 需要客户端可执行兼容版本的 `vllm`（或通过 `--vllm-bin`
指定），以及可读取的 tokenizer。 本项目不会自动安装或替换 vLLM。

bench 统一发送单条 user 消息、无准确率 system prompt，服务端只套一次模板；thinking=false、
temperature0、请求和抽样seed0、上限256、允许EOS。`request-rate=inf`，无客户端并发上限， 因此 TTFT 包含集中提交后的排队，不等于单请求延迟。服务端
max_num_seqs16 不等于客户端并发16。 图片输入 token 必须核对服务端 usage/tokenization，不能把文本估算值当完整输入量。 详见
[BENCH](docs/BENCH.md)。旧 `materialize` 命令仍只导出文本。

## 输出与证据

| 位置                          | 内容                                                 |
| ----------------------------- | ---------------------------------------------------- |
| `plan/`                       | 数据副本、题目、配置/提示词 contract、源码快照及哈希 |
| `full/solver/`、`full/judge/` | 逐题原始请求/响应、usage、finish_reason、索引        |
| `full/report/`                | summary、逐题 JSON/CSV、子集/模态/学科统计           |
| `receipt/`                    | 服务快照、原 argv/启动日志及 effective 对照结果      |
| `EVIDENCE_BUNDLE.json`        | 证据文件清单及 bundle SHA-256                        |
| `results/`、`MANIFEST.json`   | 成绩表及其与证据的哈希绑定                           |

`seal evidence → table → seal final → seal check` 完成非循环绑定；将 manifest 哈希另存目录外。 `--small-only`
只哈希模型小文件，权重仅列清单；不能宣称完整权重或 model revision 一致。 SHA-256 是一致性校验，不是数字签名。原始结果含题目、图片、参考答案及模型输出，不能直接当作公共发布包。

## 已完成验证与已知限制

- Python 3.12 客户端测试35项通过，完成 Gold668、Revision1143全量和四组图文 bench。
- Gold **156/668（23.35%）**，Revision **313/1143（27.38%）**；未判定32/40，作答截断383/688。
  这些是特定服务/profile和预算下的单次结果，不是工具安装后的预期成绩。
- xgrammar空白限制修复了最初的特定空白循环样本，但未消除重复生成或 Judge 截断；不保证全量无无效评分。
- 不输出 calibration_error；保留 confidence，原因与后续改进项见 [OPEN_ITEMS](docs/OPEN_ITEMS.md)。
- 历史准确率客户端为 `a829660`；图文 bench 客户端为 `6d0358c`。旧计划应使用其原代码， 不能因为发布版更新就替换旧计划中的源码哈希。

成绩和证据：[benchmark #280](https://github.com/vLLM-HUST/vllm-hust-benchmark/pull/280)。
展示：[website #433](https://github.com/vLLM-HUST/vllm-hust-website/pull/433)。 详细验证记录见
[VALIDATION](docs/VALIDATION.md)，证据边界见 [EVIDENCE](docs/EVIDENCE.md)。

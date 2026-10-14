# 操作步骤

**目前全量门槛尚未通过。先阅读 OPEN_ITEMS.md，解决结构化空白循环和上下文预算，再使用以下全量命令。**

以下命令在远程客户端环境执行。服务由操作者在外部启动，客户端只接收真实 argv、启动日志、profile 与 endpoint。
示例使用当前远程路径。新机器先 fetch 数据；不要重复覆盖已有目录。

```bash
cd /root/hust-eval-client-hle-verified
export PATH="$PWD/.venv/bin:$PATH"
ASSETS=/root/dataset/hle-verified/b705e0fb541c025a1532ce0d60d70ae2f53b00e0
# 新机器执行：hust-eval-hle-verified fetch --output "$ASSETS"
hust-eval-hle-verified inventory --assets "$ASSETS"
RUN=/root/runs/hle-verified/my-new-run
mkdir -p "$RUN"
cp /path/to/actual-profile.json "$RUN/profile.json"
hust-eval-hle-verified receipt --run-dir "$RUN" --base-url http://127.0.0.1:18180 \
  --profile "$RUN/profile.json" --startup-log /path/to/frozen-startup.log \
  --server-argv /path/to/actual-argv.json
hust-eval-hle-verified hash-model --model /models/Qwen3.5-35B-A3B --small-only --out "$RUN/model-small-before.json"
hust-eval-hle-verified contract --profile "$RUN/profile.json" --out "$RUN/runtime-contract.json"
hust-eval-hle-verified prepare --assets "$ASSETS" --solver-config examples/solver.json \
  --judge-config examples/judge.json --solver-runtime-contract "$RUN/runtime-contract.json" \
  --judge-runtime-contract "$RUN/runtime-contract.json" --output "$RUN/plan"
```

prepare 默认 Gold+Revision、保留所有图片。先 smoke 使用 --case-id 多次指定文本和图片的题目 ID；ID 从 plan/tasks.json 读取。
完整执行与 smoke 输出目录必须分开，不能把 --limit smoke 目录直接作为全量 resume。

```bash
hust-eval-hle-verified run --plan "$RUN/plan" --output "$RUN/full/solver"
hust-eval-hle-verified judge --plan "$RUN/plan" --responses "$RUN/full/solver" --output "$RUN/full/judge"
hust-eval-hle-verified summary --plan "$RUN/plan" --responses "$RUN/full/solver" \
  --grades "$RUN/full/judge" --output "$RUN/full/report"
```

run/judge 中断后，在完全相同命令增加 --resume。失败记录不会悄悄重试；复测另建目录。不要删除活动锁，除非确认没有客户端在运行。
图片或 structured outputs 报错时停止扩大全量，先排查服务支持，不自动丢弃图片或换解析规则。

可选文本性能探针：

```bash
hust-eval-hle-verified materialize --plan "$RUN/plan" --sample 200 --output "$RUN/bench-input.jsonl"
hust-eval-hle-verified bench --run-dir "$RUN/bench" --name hle-text \
  --dataset "$RUN/bench-input.jsonl" --base-url http://127.0.0.1:18180 \
  --served-model qwen3.5-35b --tokenizer /models/Qwen3.5-35B-A3B --num-prompts 200 --output-len 256
```

结束后，收集服务版本/设备信息及冻结日志副本；再次获取模型小文件哈希并比较。将客户端、环境和实际命令放在 RUN 内。
不要把仍在写入的服务日志直接用于封存。

```bash
hust-eval-hle-verified hash-model --model /models/Qwen3.5-35B-A3B --small-only \
  --expected "$RUN/model-small-before.json" --out "$RUN/model-small-after.json"
hust-eval-hle-verified seal evidence --run-dir "$RUN"
hust-eval-hle-verified table --run-dir "$RUN" --summary "$RUN/full/report/summary.json"
hust-eval-hle-verified seal final --run-dir "$RUN" --table "$RUN/results/hle-verified-results.md" \
  --ledger /root/runs/hle-verified/manifest-ledger.jsonl
hust-eval-hle-verified seal check --run-dir "$RUN"
```

保存 manifest_sha256 到运行目录外（ledger/Git/报告）。不要把带题目、参考答案、图片的原始运行证据直接上传公共仓库。

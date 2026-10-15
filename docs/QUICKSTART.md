# 从安装到结果封存

服务由操作者在仓库外启动和管理。以下命令只采集回执、发送请求和处理结果。 先按README安装并激活虚拟环境，调整solver/Judge配置中的地址、模型和预算。
同一模型服务可承担两种角色；若服务不同，须分别采集各自回执和runtime contract。

## 1. 数据与新运行目录

```bash
HLE_ASSETS=/data/hle-verified
HLE_ROOT=/data/runs/hle-001

# 已有数据不要覆盖，直接 inventory；新目录才执行 fetch。
hust-eval-hle-verified fetch --output "$HLE_ASSETS"
hust-eval-hle-verified inventory --assets "$HLE_ASSETS"
mkdir -p "$HLE_ROOT"
```

默认下载Gold+Revision，不含Uncertain。可通过重复`--subset`指定子集。数据下载后校验固定大小及哈希。 不要将原始数据、图片和运行答案提交公共Git仓库。

## 2. 冻结真实服务证据和评测计划

以下以Gold为例。将profile/argv/log路径替换成实际采集文件；profile里的预期配置不能代替实际回执。 复制的启动日志应已冻结，不能是仍会追加的原日志。

```bash
HLE_RUN="$HLE_ROOT/gold"
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
```

并发16是本次运行配置，不是工具强制要求。默认solver.json/judge.json仍为并发1。
实际服务参数见receipt/effective.json：检查ok、mismatches以及verified/unverified/argv_only/log_only。
配置缺乏实际证据时不能标为已验证。原日志缺失无法事后重建为真实startup receipt。 `hash-model`读取客户端可见的文件；不具有远程自动访问模型文件的能力。

操作者还应将实际启动命令、允许公开/封存的环境信息、包版本、设备信息、镜像digest及当前服务连续性 记录放入RUN。拿不到的字段写明未知；仅有同名模型不代表同一工件。详见EVIDENCE.md。

## 3. 文字、图片和Judge smoke

从`plan/tasks.json`选择一题文字和一题图片，记录case_id；不要只测试最短文本便扩大到全量。 可用以下命令列出该计划里每种模态的首题ID，另选长题检查上下文预算：

```bash
python - "$HLE_RUN/plan/tasks.json" <<'PY'
import json, sys
rows = json.load(open(sys.argv[1]))
for mode in ('text', 'image'):
    candidates = [r for r in rows if bool(r['image']) == (mode == 'image')]
    print(mode, candidates[0]['case_id'] if candidates else 'none')
PY
```

将下列两个case_id替换为上述实际ID；solver和Judge用完全相同选题列表。

```bash
hust-eval-hle-verified run --plan "$HLE_RUN/plan" --output "$HLE_RUN/smoke/solver" \
  --case-id GOLD_TEXT_CASE_ID --case-id GOLD_IMAGE_CASE_ID
hust-eval-hle-verified judge --plan "$HLE_RUN/plan" --responses "$HLE_RUN/smoke/solver" \
  --output "$HLE_RUN/smoke/judge" --case-id GOLD_TEXT_CASE_ID --case-id GOLD_IMAGE_CASE_ID
```

查看原始请求记录的status、finish_reason、usage和error，确认图片、schema支持及长题预算。
图片/结构化输出报错时先排查，不自动丢图、不换评分规则。新的模型/profile需要重新预检。 Smoke与全量用不同输出目录，不能把`--limit`或选题smoke目录直接作为全量resume。

## 4. 完整作答、评分与统计

```bash
hust-eval-hle-verified run --plan "$HLE_RUN/plan" --output "$HLE_RUN/full/solver"
hust-eval-hle-verified judge --plan "$HLE_RUN/plan" \
  --responses "$HLE_RUN/full/solver" --output "$HLE_RUN/full/judge"
hust-eval-hle-verified summary --plan "$HLE_RUN/plan" \
  --responses "$HLE_RUN/full/solver" --grades "$HLE_RUN/full/judge" \
  --output "$HLE_RUN/full/report"
```

run/judge中断后，在完全相同命令后加`--resume`。它复用已有记录，不暗中重试失败请求。
核心模块或配置改变时旧plan拒绝继续执行；使用原提交/归档源码，或新建计划，不能改哈希绕过检查。 不要删除活动锁，除非已确认没有该客户端进程或未完成的对应请求。

Gold完成后，对Revision重复第2至5步：使用`HLE_RUN="$HLE_ROOT/revision"`和`--subset revision`，
其他选项按自己的冻结配置设置。两份报告分别封存。默认prepare不指定subset会同时纳入两者， summary仍分别统计；若要复现本次组织方式，应采用两个独立计划。

## 5. 前后工件比较与准确率封存

确认所有请求结束、报告已生成，收集日志副本。以下模型比较不会计算权重哈希。

```bash
hust-eval-hle-verified hash-model --model /models/Qwen3.5-35B-A3B --small-only \
  --expected "$HLE_RUN/model-small-before.json" --out "$HLE_RUN/model-small-after.json"
python - "$HLE_RUN/model-small-before.json" "$HLE_RUN/model-small-after.json" <<'PY'
import json, sys
before, after = [json.load(open(p)) for p in sys.argv[1:]]
assert after['all_hashed_expected_matched']
assert after['expected_file_inventory_matches']
assert {k:v['bytes'] for k,v in before['files'].items()} == {k:v['bytes'] for k,v in after['files'].items()}
print('Small-file hashes and file inventory match; full weight bytes were NOT hashed.')
PY

hust-eval-hle-verified seal evidence --run-dir "$HLE_RUN"
hust-eval-hle-verified table --run-dir "$HLE_RUN" --summary "$HLE_RUN/full/report/summary.json"
hust-eval-hle-verified seal final --run-dir "$HLE_RUN" \
  --table "$HLE_RUN/results/hle-verified-results.md" --ledger "$HLE_ROOT/manifest-ledger.jsonl"
hust-eval-hle-verified seal check --run-dir "$HLE_RUN"
```

SHA-256比较不匹配时先保留记录并排查，不能继续宣称同工件。seal后不要增加或修改证据目录文件。
manifest自身哈希保存在目录外。未判定题不妨碍如实封存，但必须在成绩里报告，不能宣称全部有效判分。

## 6. 单独运行四组bench

按[BENCH.md](BENCH.md)从已封存Gold/Revision导出新目录。文本各200、图片全部93/118。
准确率结束、服务空闲且连续性/实际配置复核通过后，先做图片小样本，再顺序压测，不并行抢同一服务。 bench输出含命令、冻结输入、manifest、语义说明、日志、详细原始结果和summary。

工具的bench子命令不会自动完成服务器端tokenization核验，也不会自动收集完整环境或封存全部四组。
操作者须核对实际usage与图片输入token，收集服务连续性回执、模型前后清单等，再将四组目录一起封存：
`seal evidence`后，在`results/`写性能结果表并引用evidence_bundle_sha256；
然后`seal final --table ... --ledger ...`及`seal check`。`table`子命令目前生成的是准确率表。

任何复测用新的运行目录，不覆盖旧结果，也不把多个profile下的记录混成一次测量。

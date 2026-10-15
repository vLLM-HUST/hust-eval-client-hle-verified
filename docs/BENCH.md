# HLE-Verified 文本和图片压测

这是向既有服务发送请求的客户端，不负责启动或改变 vLLM 服务。

## 从已封存准确率结果导出独立输入

```bash
hust-eval-hle-verified bench-materialize --accuracy-run /runs/accuracy/full-gold --modality text --sample 200 --output /runs/bench/exports/gold-text
hust-eval-hle-verified bench-materialize --accuracy-run /runs/accuracy/full-gold --modality image --output /runs/bench/exports/gold-image
```

Revision 同理。正式方案：Gold 文本 200/575，Revision 文本 200/1025；Gold 图片全部 93，Revision 图片全部 118。文本按冻结 tasks 的原顺序筛选，再取 `floor(i*N/200)`，不重复、不按答对与否筛选。图片保留原题文字和原始 data URL，逐图记录解码字节 SHA-256。

导出先验证准确率目录的最终 seal、结果表与任务文件哈希。生成新 bench 输入并引用旧 manifest、evidence bundle、contract 和源码版本，不修改旧计划、不绕过 `load_plan` 的源码校验。旧准确率计划仍须用原客户端重放。导出是独立的封存数据导入流程，不代表用新版客户端恢复旧准确率任务。

## 发起压测

```bash
hust-eval-hle-verified bench --run-dir /runs/bench/gold-image --name gold-image --dataset /runs/bench/exports/gold-image/prompts.jsonl --input-manifest /runs/bench/exports/gold-image/prompts.jsonl.manifest.json --modality image --base-url http://127.0.0.1:18180 --served-model qwen3.5-35b --tokenizer /models/Qwen3.5-35B-A3B --num-prompts 93 --output-len 256
```

文本使用 `--modality text --num-prompts 200`。要求安装的 vLLM 支持 `custom_image`、`--skip-chat-template`、`--extra-body` 和 `--save-detailed`。每组使用独立目录；输入或结果存在即拒绝覆盖，失败结果保留。

四组共同协议：单条 user 消息、原题文字及存在的图片、不加准确率测试的 system prompt；服务端模型聊天模板只套一次（文本启用 skip-chat-template 避免客户端重复渲染）；显式 `enable_thinking=false`、temperature=0、请求 seed=0、采样 seed=0、ignore_eos=false；最多 256 token，允许 EOS 提前结束。request-rate=inf，无客户端 max-concurrency；服务 max_num_seqs=16 并非固定客户端并发 16。vLLM 自带的首题测试请求在正式计时范围之外，另设 warmups=0。此性能协议与准确率请求不同，也不能直接宣称与旧版客户端 bench 完全同口径。

安装版本的 openai-chat 后端优先采用 SSE usage.prompt_tokens；缺失时回落到文本长度估计。图片预估长度不包含视觉 token，因此必须保留 detailed input_lens，并与相同消息和模板参数的服务端 /tokenize 逐题核对。未经核对，不把文本估计说成完整输入 token，不报告可信的总 token 吞吐。输出吞吐、TTFT、TPOT 原始值仍保留；实际 token 数和协议差异一并报告。

## 证据

保存命令 argv、输入及 manifest、逐图字节哈希、客户端 git 版本/源码、安装的 vLLM 相关源码、请求构建验证、功能 smoke、正式原始结果和每题 token 校验。服务 startup/effective 回执须由操作者提供，并确认仍为同一运行服务；客户端不会自动获得容器镜像 digest。模型仅哈希小文件，权重只列清单，不能据此声称完整权重一致。

四组完成并停止写入后，使用 `seal evidence` 生成 evidence_bundle_sha256，写入性能结果表，再执行 `seal final --table ... --ledger ...` 和 `seal check`，manifest 哈希另存目录外。切勿把运行中的日志直接纳入 seal。

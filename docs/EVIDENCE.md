# 冻结证据

继承 FrontierScience 客户端 dbb34c9e4bb267a1cd43082aefd0285b2696221c 的 hashing/config_check/receipt/runtime_contract/bench/seal 基础逻辑；不依赖外部客户端仓库。HLE 独立协议和解析在本仓库。

需操作者提供并冻结：

- 模型绝对路径、文件清单、小文件 SHA-256；--small-only 不证明权重字节一致、也不验证预期 revision。
- 完整服务启动命令、实际 argv、环境变量、启动日志、版本、硬件、镜像 digest（拿不到必须 NOT_PROVIDED）。
- dtype、TP/PP/DP/EP/DCP、disable_custom_all_reduce、gpu_memory_utilization、max_model_len、max_num_seqs、max_num_batched_tokens、prefix/chunked/speculative、eager/compile/cudagraph/capture sizes。
- receipt 比较实际 argv、日志与 profile。无日志不能追溯重建，预期值不能冒充 effective；unverified/argv_only/log_only 保留区别。
- 计划绑定数据 LFS SHA-256、子集和模态、官方提示词来源、模型和 Judge 参数、源代码哈希。
- 每题完整请求/响应、finish_reason、token usage、耗时、状态、结构化判分；Judge 与 solver record 严格关联。

seal evidence 冻结 results/ 之外文件清单；table 将 bundle hash 写入结果表；seal final 记录 bundle hash+表文件 SHA-256；manifest 自身哈希在目录外保存，避免循环。
seal check 同时核查文件清单、bundle digest、manifest 绑定与表哈希。这是普通 SHA-256 清单，不是数字签名。
未取得 startup receipt 的测试只能说明客户端功能，不能声称真实服务参数已验证。

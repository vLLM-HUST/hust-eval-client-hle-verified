# 验证记录

日期：2026-10-14。开发、测试和数据均在远程容器。

- Python 3.12：30 项单元/HTTP 集成测试通过，包含真实本地 HTTP 模拟服务，无 NPU 请求冒充成绩。
- Python 3.9 语法解析通过；当前未执行 3.9 运行时测试，GitHub CI 已配置 3.9/3.12，但尚未在 GitHub 运行。
- wheel 无依赖安装至独立虚拟环境成功，CLI --version/--help 成功。
- 固定上游作答/Judge 提示词 AST 字符串逐字匹配；response_format 与官方类经 OpenAI SDK 生成的 JSON schema 相等。
- Gold/Revision 固定 LFS 大小与 SHA-256 校验通过；总1811题、图片211题。
- receipt SameFileError（已冻结 profile 被再次复制到自身）已修复并加入回归测试。首次准备失败保留，无模型请求，无测试成绩。
- 证据校验增加 bundle digest 自洽检查和 manifest→bundle 绑定检查。

## 真实 smoke

运行目录：/root/runs/hle-verified/hle-qwen35-smoke-20261014T054612Z。

- 18项服务 effective 参数通过 argv+startup log 核对。
- Gold/Revision各文本和图片一题：4条solver HTTP成功，1条length。
- Judge：3条正常stop且JSON有效，1条在strict字段后空白循环到8192而invalid；没有正则补分。
- 2条纯文本bench成功，0失败；只验证接口，不作为性能成绩。
- 211张数据图片验证通过，3道Revision长题存在最坏输出预算下的Judge上下文风险。
- 模型11个小文件前后匹配；14个权重文件仅列出，未计算SHA-256。
- 原始求解/评分使用plan/client_source中冻结的源码。后续修复hash-model的expected映射格式兼容性，原始请求、判分和plan未改动；辅助哈希/封存源码另存tooling-postfix，恢复过程有recovery.json。
- hash-model现在支持benchmark文件列表和自身文件映射两种格式；跳过权重不被误报为完全一致。
- 本轮自建服务在bench后已停止；未开启全量。

见OPEN_ITEMS.md中的候选修复；尚未完成调整后的复验。


## 冻结锚点

- evidence_bundle_sha256: `da71f5658517e71ea2ec87df4a59da78de0ee651946a9a5a008f8ace9df46b31`
- table_sha256: `42c43b00385f2e773a0e174c96a651d7d9854b4f0a8202c45f2daace915687b6`
- manifest_sha256: `b91994583c1623c5efe5e891f59c476bcba0b9738af30e1019ad0bb9c97ce454`
- seal check: 107个证据文件一致，结果表、bundle digest、manifest关联均通过。
- 最终wheel SHA-256: `b535f7def03ebc654dd1caf4666ced8834307aa1e6b6ba63fd4ff673b15cb198`；独立wheel安装环境再次30项测试通过。

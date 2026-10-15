# 验证记录

## 已完成运行（2026-10-14/15）

原始准确率版本 `a829660ca4d91a103ad77f7cc768bda140974723`，并发16；图文bench版本
`6d0358cba5f7f136123efae90c3ffe6072183113`。后续文档更新不改写这些运行记录。

| 子集     | 作答请求完成 | 有效Judge | 正确 / 总数 | Judge未判定 | 作答截断 |
| -------- | -----------: | --------: | ----------: | ----------: | -------: |
| Gold     |      668/668 |       636 |     156/668 |          32 |      383 |
| Revision |    1143/1143 |      1103 |    313/1143 |          40 |      688 |

有效请求数不等于答对数。未判定留在全部题目分母中，不代表已确认答错。 四组bench分别完成200/200、200/200、93/93、118/118，零失败；图片保留原始字节，611题输入长度
均与同服务tokenization一致。安装版请求构造检查覆盖全部611题，另有2道真实图片smoke。

20项实际服务配置均通过argv/startup核验。模型小文件前后匹配，权重仅列清单。 三份原始封存清单均复验通过：

| 运行     | MANIFEST SHA-256                                                 |
| -------- | ---------------------------------------------------------------- |
| Gold     | e5fa4355cb4034c273fcd3c784e2a36bad66f5ceeb2af63717b3a38131252794 |
| Revision | 83dde635173f5643ac278f4dd578d40b64c37ffb530fa8cd870881d46d3957c0 |
| bench    | 238f8d90d7cc56cc2181425ff2cf3eca625a86b867886e03959c6e53c7803c3a |

公开成绩和证据在 [benchmark #280](https://github.com/vLLM-HUST/vllm-hust-benchmark/pull/280)， 展示在
[website #433](https://github.com/vLLM-HUST/vllm-hust-website/pull/433)。这两项提交CI通过，
但不能据此宣称本客户端首次发布的CI已经运行；客户端CI状态以本仓库Actions为准。

## 客户端功能测试

图文bench版本的Python3.12测试35项通过，覆盖本地HTTP请求、冻结计划源码检查、续跑记录、
JSON判分、回执匹配、模型小文件比较、证据seal、不可变成绩导入、采样和图片字节哈希校验。
这些功能测试不能代替真实模型成绩。CI矩阵为Python3.9/3.12，并检查wheel安装、CLI入口与源码清单。

固定上游system/judge提示词AST字符串逐字匹配；response_format与官方类经SDK生成的JSON schema一致。
Gold/Revision固定LFS大小与SHA-256均校验通过，全部211张图片完成验证。

## 早期验证与修复历史

- 最初4题smoke：solver4条成功、1条length；Judge3条有效、1条JSON空白循环截断。
- 32768上下文存在长题预算风险，外部操作者切换65536服务，并开启xgrammar空白限制。
- 原始失败Judge请求不变重放：130token，stop，完整JSON；1811题tokenization预检完成。
- 补充11题覆盖Gold/Revision、文本/图片、两类答案和长题：solver11条成功、Judge11条有效。
- 用户随后由并发1改4再改16；旧的21条/13条部分运行保留为未完成记录，不混入全量成绩。
- 同模型、单次评测、严格JSON口径始终保留；完整结果仍有72条Judge截断，见OPEN_ITEMS。

最初smoke的历史manifest锚点为 `b91994583c1623c5efe5e891f59c476bcba0b9738af30e1019ad0bb9c97ce454`，不得替代本次全量锚点。

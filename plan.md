# JUCE Agent Reference 项目计划

## 1. 文档地位

本文档定义 JUCE Agent Reference 项目的：

- 最终目标
- V1 范围
- 总体架构
- 核心设计原则
- 自动执行边界
- 里程碑
- 验收标准

本文档是项目的架构与范围基准。

相关文档职责如下：

| 文档                | 职责                                         |
| ------------------- | -------------------------------------------- |
| `AGENTS.md`         | 规定 Agent 的执行协议、恢复规则和停止条件    |
| `plan.md`           | 规定项目目标、架构、范围与最终验收标准       |
| `implementation.md` | 规定具体模块、接口、实现顺序、测试和提交规则 |

执行 Agent 不得擅自修改本文档中的核心架构、V1 范围或验收标准。

如果实施过程中发现本文档与真实 JUCE 或 Doxygen 行为存在差异，Agent 应优先通过兼容性实现、测试夹具和内部扩展解决；只有要求确实互相矛盾、无法同时满足时，才允许将其认定为外部阻断。

------

# 2. 项目目标

构建一个与指定 JUCE commit 严格对应的本地 Agent 参考系统，使编程 Agent 能够可靠回答以下三类问题。

## 2.1 API 是什么

Agent 能够查询：

- 类
- 结构体
- 命名空间
- 模块
- 方法
- 构造函数
- 枚举
- 类型别名
- 宏
- 参数
- 返回值
- 继承关系
- deprecated 信息
- note、warning 和相关引用

这些信息主要通过本地 Markdown API 文档提供。

## 2.2 API 应该怎样使用

Agent 能够找到：

- JUCE 官方示例
- API 文档注释中的代码片段
- 示例所使用的 JUCE 符号
- 与目标 API 相关的真实 `.h`、`.cpp`、`.mm` 等代码文件

完整示例代码保持原始源文件形式，不复制成大型 Markdown。

## 2.3 API 如何声明或实现

Agent 能够定位：

- 同版本 JUCE 头文件中的声明位置
- Doxygen 能可靠提供的实现位置
- 相关源文件
- 声明与文档之间的对应关系

不确定的定义位置不得通过正则或启发式猜测伪造。

------

# 3. 最终用户体验

在目标 JUCE 项目中，Agent 应能够执行类似命令：

```powershell
juce-doc symbol "juce::AudioProcessor"
juce-doc show "juce::AudioProcessor::processBlock"
juce-doc search "save plugin parameter state"
juce-doc examples "juce::AudioProcessorValueTreeState"
juce-doc source "juce::Component::repaint"
juce-doc related "juce::AudioProcessor"
juce-doc verify --juce-root .\JUCE --reference .\.agent-docs\juce
```

查询结果必须提供：

- 准确的 symbol
- 类型或成员种类
- 所属模块
- Markdown 文档路径
- 成员锚点
- 简要说明
- 完整签名
- 声明位置
- 可用的官方示例
- 结果置信度或来源类型

即使专用 CLI 暂时不可用，Agent 仍应能够直接使用：

```powershell
rg -i "AudioProcessorValueTreeState" juce-reference
```

搜索 Markdown、TSV 和 JSONL 索引。

因此，纯文本产物是核心，SQLite 等数据库只是可重建的增强缓存。

------

# 4. 核心设计原则

## 4.1 使用本地 JUCE 源码作为版本事实

项目必须从调用者指定的本地 JUCE checkout 生成参考库。

文档身份必须绑定完整 Git commit SHA，不能仅记录：

- `develop`
- `master`
- `latest`
- release 名称但无 commit

如果 JUCE 工作区存在未提交修改，默认拒绝生成正式版本。

允许通过显式选项生成 dirty 版本，但必须：

- 标记 `dirty: true`
- 标记为不可正式发布
- 不允许替换稳定的 `current` 版本

## 4.2 不爬取 JUCE API 网页

API 文档管线固定为：

```text
JUCE modules
    ↓
JUCE 官方 Doxygen 配置
    ↓
Doxygen XML
    ↓
规范化内部模型
    ↓
Markdown 和索引
```

不得使用网页 HTML 抓取替代 Doxygen XML。

原因包括：

- HTML 页面结构不稳定
- 存在导航和布局噪声
- 类型信息不如 XML 明确
- 交叉引用不如 `refid` 可靠
- 难以绑定准确源码 commit
- 容易产生静默内容丢失

## 4.3 保持 `XML_PROGRAMLISTING = NO`

V1 必须使用：

```text
XML_PROGRAMLISTING = NO
```

其含义是避免将完整源文件代码清单写入 Doxygen XML。

它不能导致以下信息丢失：

- API 声明
- 函数签名
- 模板参数
- 默认参数
- `const`
- `noexcept`
- `override`
- 文档注释中的代码块
- `\code` 或 Markdown fenced code
- 参数和返回值说明

完整源码通过源码索引查询，完整官方示例通过示例索引查询。

文档、示例和源码各自承担不同职责：

```text
Markdown 文档解释 API
官方示例展示正确用法
同版本源码确认最终事实
```

## 4.4 不把所有内容合并成巨大 Markdown

不得生成单一巨型 API Markdown 作为主要查询入口。

采用：

- 一个主要类型一个 Markdown 页面
- 成员保留在所属类型页面
- 成员使用稳定显式锚点
- 模块和命名空间独立成页
- 第一方仓库指南独立保存

这样能够保留类型上下文，也避免方法级文件数量失控。

## 4.5 转换必须经过规范化内部模型

Doxygen XML 不得直接边解析边拼接 Markdown。

固定边界：

```text
Doxygen XML Parser
        ↓
Canonical IR
        ├─ Markdown Renderer
        ├─ Symbol Index Builder
        ├─ Relationship Index Builder
        ├─ Source Location Indexer
        └─ Validation
```

内部模型的目的：

- 分离 XML 解析和 Markdown 表现
- 支持稳定测试
- 允许以后增加新的输出形式
- 防止 Doxygen XML 细节泄漏到全部模块
- 让未知语义节点能够被准确发现

## 4.6 不自动改写官方内容

生成器可以：

- 转换结构
- 修复本地路径
- 生成标题和元数据
- 去除完全重复的 brief/details
- 构建索引
- 生成导航

生成器不得：

- 自动翻译
- AI 总结
- AI 补全文档
- 编造示例
- 改变 API 含义
- 根据语义相似度删除官方内容
- 把内部用法描述为官方推荐用法

------

# 5. 事实来源优先级

当不同生成物或数据源存在差异时，使用以下优先级：

```text
1. 当前锁定 commit 的 JUCE 源码
2. 同一 checkout 生成的 Doxygen XML
3. 同一 commit 中的 JUCE 官方 Markdown
4. 同一 commit 中的 JUCE 官方 examples
5. 生成后的 Markdown 和索引
6. 搜索数据库缓存
```

生成后的文档和数据库只是可检索表示，不是独立事实来源。

任何索引均必须能够追溯到：

- Doxygen refid
- JUCE 源文件
- JUCE 官方文档文件
- JUCE 官方示例文件

------

# 6. V1 必须完成的范围

## 6.1 可复现的文档生成

V1 必须支持：

- 校验 JUCE checkout
- 读取完整 commit SHA
- 检查 dirty 状态
- 锁定 Doxygen 精确版本
- 使用 JUCE 官方 Doxyfile
- 通过 overlay 修改输出配置
- 不修改 JUCE 仓库文件
- 生成 Doxygen XML
- 校验 Doxygen XML Schema
- 记录工具链版本

## 6.2 Doxygen XML 转换

V1 必须支持：

- class
- struct
- union
- namespace
- group/module
- Doxygen page
- 必要的 file compound
- constructor
- destructor
- method
- operator
- function
- enum
- enum value
- field
- typedef
- using alias
- macro
- template parameter
- function parameter
- return description
- throws description
- deprecated
- note
- warning
- internal reference
- external link
- inline code
- documentation code block
- list
- table
- section
- formula
- 图片引用的安全处理

所有 Doxygen entity 必须具有明确处理结果：

```text
rendered
indexed-only
skipped-with-reason
```

禁止无记录地丢弃 entity。

## 6.3 Markdown API 参考库

V1 必须生成：

- 类型页面
- 模块页面
- 命名空间页面
- Doxygen page
- 必要的文件页面
- 成员索引
- 成员详情
- 继承关系
- 相关符号
- 声明位置
- 官方示例反向链接
- 稳定成员锚点
- 本地相对 Markdown 链接
- JUCE commit 元数据

## 6.4 JUCE 第一方指南

V1 必须导入同一 commit 下可用的官方 Markdown，包括：

```text
JUCE/docs/*.md
JUCE/README.md
JUCE/BREAKING_CHANGES.md
```

处理原则：

- 保留正文原文
- 添加最小版本元数据
- 修复可确定解析的本地链接
- 保留外部链接
- 不重新总结或翻译

## 6.5 符号和关系索引

V1 必须生成：

- `symbols.tsv`
- `symbols.jsonl`
- `relationships.jsonl`
- `source-locations.jsonl`
- `examples.jsonl`
- `manifest.json`

符号索引必须覆盖 compound 和 member。

成员虽然不生成独立 Markdown 文件，但必须是独立可查询 symbol。

## 6.6 全文搜索

V1 必须提供：

- 精确 symbol 查询
- 短名称查询
- 人工别名查询
- CamelCase 分词查询
- 签名查询
- brief 查询
- 正文全文查询
- 示例概念查询
- 稳定排序
- 机器可读 JSON 输出

SQLite FTS5 可以用于性能增强，但：

- 不能是唯一事实来源
- 必须可以从文本产物重建
- 删除数据库后不能导致文档信息丢失

## 6.7 官方示例索引

V1 必须扫描：

```text
JUCE/examples
```

并生成：

- 示例名称
- 示例分类
- 源文件路径
- 使用的完整限定 JUCE symbol
- symbol 出现位置
- 关联置信度
- 示例 Markdown 导航页
- 从 API 页面到示例的反向链接

第一版只要求使用确定性的符号关联，例如：

- 完整限定名
- 明确的 `juce::<Symbol>` 引用
- 已知索引 symbol 的准确文本匹配

不得把短名称的普通文本出现直接认定为高置信度关联。

## 6.8 源码定位

V1 必须支持：

- Doxygen location 提供的声明位置
- Doxygen body location 提供的实现位置
- 源文件路径
- 行号
- 来源和置信度

如果实现位置无法可靠确定，必须返回：

```text
Definition not resolved
```

而不是猜测。

## 6.9 验证和原子发布

V1 必须提供：

- XML 验证
- IR 完整性验证
- Markdown 链接验证
- 锚点验证
- 路径冲突验证
- 索引路径验证
- 示例文件验证
- 源码位置验证
- 搜索质量验证
- JUCE commit 一致性验证
- 确定性验证
- 原子发布
- 失败回滚或保留旧版本

------

# 7. V1 明确不包含的范围

以下能力不属于 V1 Definition of Done：

- JUCE 教程网站抓取
- `docs.juce.com` HTML 抓取
- JUCE 论坛抓取
- 向量数据库
- embedding 搜索
- MCP Server
- HTTP 服务
- Web UI
- AI 自动总结
- AI 自动翻译
- AI 自动生成示例
- 完整 Clang AST 索引
- Tree-sitter 全项目语义分析
- 对 `JUCE/extras` 的深度分析
- 跨多个 JUCE 版本同时查询
- 自动修改用户 JUCE 项目
- 自动迁移旧 JUCE API

可以预留 Provider 接口支持未来扩展，但不得因为这些延期功能阻塞 V1。

------

# 8. 输出结构

正式参考库采用以下逻辑结构：

```text
juce-reference/
├─ README.md
├─ AGENTS.md
├─ docs.lock.json
├─ manifest.json
│
├─ reference/
│  ├─ INDEX.md
│  ├─ modules/
│  ├─ types/
│  ├─ namespaces/
│  ├─ pages/
│  └─ files/
│
├─ guides/
│
├─ examples/
│  ├─ INDEX.md
│  ├─ plugins.md
│  ├─ dsp.md
│  ├─ audio.md
│  ├─ gui.md
│  ├─ midi.md
│  ├─ utilities.md
│  └─ other.md
│
├─ index/
│  ├─ symbols.tsv
│  ├─ symbols.jsonl
│  ├─ relationships.jsonl
│  ├─ examples.jsonl
│  ├─ source-locations.jsonl
│  └─ search.sqlite
│
└─ reports/
   ├─ validation.json
   ├─ generation.json
   ├─ doxygen-warnings.log
   ├─ formatting-warnings.json
   └─ skipped-entities.json
```

正式参考库不复制完整 JUCE checkout。

Markdown 和索引通过相对路径或配置的 JUCE 根路径定位原始源码和示例。

------

# 9. Markdown 页面粒度

## 9.1 独立页面

以下实体生成独立页面：

- class
- struct
- union
- namespace
- group/module
- Doxygen page
- 存在独立公共内容的文件 compound

## 9.2 所属页面内成员

以下实体保留在所属页面：

- constructor
- destructor
- method
- operator
- enum
- enum value
- field
- typedef
- using alias
- property
- macro

这样能够：

- 保留类级上下文
- 避免产生大量碎片化文件
- 方便 Agent 一次读取完整 API
- 让重载方法共享同一类型背景
- 保持文件规模可控

## 9.3 稳定锚点

成员锚点不得依赖 Markdown Renderer 自动生成。

锚点必须由稳定的 Doxygen member refid 派生。

需要保证：

- 重载方法不会冲突
- 模板和 operator 不会产生非法锚点
- 相同输入重复生成相同锚点
- 不同平台生成相同锚点

------

# 10. 搜索设计

Agent 查询分为三类。

## 10.1 精确符号查询

例如：

```text
juce::AudioProcessor
juce::AudioProcessor::processBlock
AudioProcessorValueTreeState
```

排序优先级：

```text
完整限定名完全匹配
> 短名称完全匹配
> 人工别名完全匹配
> 名称前缀匹配
> CamelCase 分词匹配
> 签名匹配
> brief 匹配
> 正文匹配
```

## 10.2 自然语言任务查询

例如：

```text
save plugin parameter state
smooth parameter changes
create a DSP processor chain
resize plugin editor
read MIDI message timestamp
```

结果必须优先返回：

- 公开且已文档化的 API
- 官方示例
- 官方指南
- 相关成员

未文档化或内部符号不得无理由排在公开 API 前面。

## 10.3 结构浏览

Agent 可以通过：

- `reference/INDEX.md`
- 模块页面
- 命名空间页面
- 继承关系
- related 查询

逐层浏览相关 API。

------

# 11. 别名策略

V1 支持两类别名。

## 11.1 自动别名

例如：

```text
AudioProcessorValueTreeState
Audio Processor Value Tree State
audio processor value tree state
```

自动缩写只作为低权重候选，不能自动获得与官方名称相同的权重。

## 11.2 人工别名

人工维护少量高价值 JUCE 术语：

```yaml
juce::AudioProcessorValueTreeState:
  aliases:
    - APVTS
    - plugin parameter state
  concepts:
    - save plugin parameter state
    - restore plugin parameter state
```

人工别名引用不存在的 symbol 时，构建必须失败，防止配置长期失效。

------

# 12. 可复现性要求

以下输入组合定义一个唯一正式版本：

```text
JUCE commit
Doxygen 精确版本
生成器版本
IR Schema 版本
Markdown Schema 版本
索引 Schema 版本
别名配置
生成配置
```

相同输入必须产生逻辑一致的正式输出。

正式输出必须遵守：

- UTF-8
- LF 换行
- 固定排序
- 固定 JSON key 顺序
- 固定 JSONL 行顺序
- 固定 TSV 行顺序
- 不在正式 Markdown 中写当前时间
- 不使用随机 ID
- 不依赖文件系统遍历顺序
- 不依赖操作系统默认 locale
- 路径使用规范化相对 POSIX 形式

SQLite 文件本身不要求跨 SQLite 版本逐字节一致，但其逻辑导出内容必须一致。

------

# 13. Fail-closed 验证原则

构建不得以“尽量生成”为目标。

遇到可能改变 API 语义或链接完整性的错误时，必须停止发布。

## 13.1 必须失败的情况

- XML Schema 不通过
- compound 文件缺失
- 重复 compound refid
- 重复 member refid
- 未识别的签名语义节点
- 未识别的参数语义节点
- 文档代码节点无法可靠保留
- 内部引用无法解析
- Markdown 内部链接损坏
- 成员锚点不存在
- 输出路径冲突
- symbol 索引指向不存在文件
- source location 指向不存在文件
- 人工别名指向不存在 symbol
- JUCE commit 不匹配
- 正式 release 内容与同 commit 的已有 release 不一致
- 最终统一验收命令返回非零

## 13.2 可以降级并警告的情况

- 纯样式 XML 节点无法等价表达
- 外部链接当前不可访问
- 图片无法本地下载但原始链接可保留
- 非语义排版细节不完全一致

降级时必须：

- 保留可用文本
- 记录明确 warning
- 不改变 API 含义
- 不伪装成完整等价转换

------

# 14. 自动化执行要求

该项目的正式目标包括：

> Agent 在读取 `AGENTS.md`、`plan.md` 和 `implementation.md` 后，可以从空项目骨架持续执行到 V1 全部完成，过程中不要求用户进行普通实现决策。

## 14.1 自动执行必须覆盖

Agent 必须能够自行完成：

- 仓库初始化
- Python 项目配置
- 模块实现
- 测试夹具
- 单元测试
- 集成测试
- 真实 JUCE smoke test
- CLI 实现
- 文档生成
- 索引生成
- 搜索质量调整
- 错误修复
- 回归测试
- Git 本地提交
- 进度状态维护
- 最终验收

## 14.2 普通问题不得请求用户决策

以下情况属于 Agent 自行解决范围：

- 测试失败
- lint 失败
- 类型检查失败
- Doxygen warning
- 新的 Doxygen XML 节点
- Markdown 链接损坏
- 路径冲突
- Windows 与 Linux 路径差异
- 搜索排序不符合预期
- Fixture 不完整
- 实现需要内部重构
- 某个方法需要增加回归测试
- 依赖的小版本兼容问题

处理循环固定为：

```text
发现失败
→ 保存完整错误
→ 缩小失败范围
→ 创建或补充最小回归测试
→ 修改实现
→ 运行局部测试
→ 运行阶段测试
→ 继续后续任务
```

## 14.3 自动进度恢复

Agent 必须维护机器可读进度状态，例如：

```text
.agent/progress.json
```

至少记录：

- 当前 Phase
- 已完成 Phase
- 最近验证 commit
- 最近成功命令
- 当前失败
- 下一步动作

执行被中断后，Agent 必须先读取：

- `AGENTS.md`
- `plan.md`
- `implementation.md`
- `.agent/progress.json`
- Git 历史
- Git 工作区

然后从最后已验证状态继续，而不是重新开始。

## 14.4 Git 行为

无人值守执行期间：

- 每个 Phase 至少一个本地 commit
- commit 范围必须清晰
- 不自动 push
- 不 force push
- 不改写远程历史
- 不提交 JUCE checkout
- 不提交临时 XML
- 不提交 `.build`
- 最终工作区必须干净

------

# 15. 允许停止的外部阻断

只有以下情况允许 Agent 在 V1 未完成前停止：

1. 指定 JUCE checkout 不存在。
2. JUCE checkout 不完整或不是有效仓库。
3. 必需工具缺失且无法在当前权限下安装或取得。
4. 必需操作要求管理员权限，但当前环境未授权。
5. 网络完全不可用，且必要依赖没有本地缓存。
6. 文件系统不可写或磁盘空间不足。
7. 内存、进程或操作系统故障导致任务无法继续。
8. 安全策略明确禁止必需操作。
9. `plan.md` 与 `implementation.md` 存在无法同时满足的实质性矛盾。

以下情况不能作为停止理由：

- 代码较复杂
- 测试较多
- XML 节点此前未实现
- 需要重构
- 搜索效果不理想
- 某个跨平台测试失败
- Doxygen 产生 warning
- 实现时间较长

发生真正外部阻断时，Agent 必须写入：

```text
.agent/blocker.json
```

包括：

- 阻断命令
- 完整错误
- 已尝试措施
- 当前 commit
- 已完成 Phase
- 恢复所需的唯一外部动作

------

# 16. 里程碑

## M1：可复现输入

完成：

- JUCE checkout 校验
- commit 和 dirty 状态
- Doxygen 版本锁定
- Doxyfile overlay
- XML 生成
- XML Schema 校验

验收：

- 相同 checkout 可重复生成合法 XML 输入
- 不修改 JUCE 工作区
- 版本不一致时明确失败

## M2：规范化模型和 Markdown

完成：

- Canonical IR
- XML Parser
- 全局路径映射
- 类型、模块和命名空间页面
- 成员签名和详情
- 文档代码块
- 稳定锚点
- 内部相对链接
- 官方仓库 Markdown 导入

验收：

- 代表性 JUCE API 能完整渲染
- 文档代码块未丢失
- 完整源文件未复制到 API Markdown
- 内部链接为零损坏

## M3：符号和全文检索

完成：

- TSV
- JSONL
- 关系索引
- 别名
- SQLite FTS5
- symbol、show、search、related

验收：

- 精确 symbol 查询稳定第 1
- 人工别名目标进入 Top 3
- 典型任务查询目标进入 Top 5
- 删除 SQLite 后可以重建

## M4：官方示例

完成：

- 扫描 `JUCE/examples`
- 示例分类
- 确定性 symbol 关联
- 示例 JSONL
- 示例 Markdown 导航
- API 反向链接
- examples 查询

验收：

- Agent 能从 API 找到真实官方示例
- 结果标记来源和置信度
- 不把内部调用误标记成官方示例

## M5：源码定位

完成：

- 声明位置
- Doxygen body location
- source 查询
- 路径验证
- 置信度记录

验收：

- 声明路径和行号准确
- 可用的定义位置准确
- 不确定位置明确返回未解析

## M6：自动验收和发布

完成：

- doctor
- 全量测试
- lint
- 类型检查
- smoke test
- 搜索质量测试
- 确定性测试
- verify
- 原子发布
- 自动恢复状态
- 最终统一验收命令

验收：

- 失败构建不覆盖旧版本
- 同一输入逻辑输出一致
- 最终统一验收命令返回 0
- Git 工作区干净

------

# 17. 统一机器验收

项目必须提供一个统一命令，完成全部最终检查。

命令名称由 `implementation.md` 固定，语义必须等价于：

```text
environment doctor
→ unit tests
→ integration tests
→ lint
→ type check
→ generate reference
→ validate output
→ real JUCE smoke test
→ search quality tests
→ determinism tests
→ version verify
→ repository cleanliness check
```

只有该命令返回退出码 `0`，Agent 才允许声明 Goal 完成。

不得通过以下方式让统一验收通过：

- 跳过失败测试
- 将失败改为 warning
- 删除验收项
- 降低搜索排名要求
- 禁用真实 JUCE smoke test
- 使用空 fixture 替代真实测试
- 保留核心 TODO 或占位实现

------

# 18. 最终 Definition of Done

只有以下项目全部满足，V1 才算完成。

## 输入与版本

-  可以校验指定 JUCE checkout。
-  文档绑定完整 JUCE commit。
-  dirty checkout 默认被拒绝。
-  Doxygen 使用锁定的精确版本。
-  JUCE 官方 Doxyfile 未被修改。
-  Doxygen overlay 可复现。
-  `XML_PROGRAMLISTING = NO`。

## XML 和内部模型

-  XML 通过 Schema 校验。
-  Doxygen XML 转换为规范化 IR。
-  每个 compound 有明确处理结果。
-  每个 member 有明确处理结果。
-  未知语义节点不会被静默忽略。
-  文档代码块被完整保留。

## Markdown

-  一个主要类型对应一个 Markdown 页面。
-  成员保留在所属类型页面。
-  重载成员具有不同稳定锚点。
-  完整函数签名被保留。
-  模板、默认参数和限定符被保留。
-  deprecated、note、warning 和 return 信息被保留。
-  所有内部链接有效。
-  所有成员锚点有效。
-  完整源文件未复制进 API Markdown。
-  官方仓库 Markdown 已导入。

## 检索

-  `symbols.tsv` 可用。
-  `symbols.jsonl` 可用。
-  关系索引可用。
-  SQLite FTS5 可重建。
-  精确 symbol 查询稳定排第 1。
-  人工别名目标进入 Top 3。
-  典型自然语言目标进入 Top 5。
-  `rg` 可独立查询 Markdown 和文本索引。

## 示例和源码

-  `JUCE/examples` 已被索引。
-  官方示例保持原始源文件形式。
-  API 页面可以反向定位官方示例。
-  示例关联具有明确来源和置信度。
-  声明位置可准确查询。
-  可用的实现位置可准确查询。
-  无法确定的实现位置不会被猜测。

## 稳定性和发布

-  输出路径在 Windows 语义下无冲突。
-  所有索引路径存在。
-  所有源码和示例路径存在。
-  相同输入产生逻辑一致输出。
-  构建失败不会覆盖旧版本。
-  同 commit 已有 release 不会被不同内容静默覆盖。
-  `verify` 能发现 JUCE commit 不匹配。
-  自动进度恢复可用。
-  最终统一验收命令返回 0。
-  Git 工作区干净。
-  不存在 blocker 文件。
-  不存在未解释的 skipped test。
-  不存在核心 TODO、`pass` 或占位实现。

------

# 19. 禁止的简化和伪完成

执行 Agent 不得：

1. 用网页抓取替代 Doxygen XML。
2. 启用 `XML_PROGRAMLISTING = YES` 规避源码定位实现。
3. 把整个 JUCE 源码复制成 Markdown。
4. 为每个方法生成独立 Markdown 文件。
5. 让 SQLite 成为唯一可查询来源。
6. 忽略无法解析的内部引用。
7. 用正则猜测不确定的 C++ 定义位置。
8. 自动改写、总结或翻译官方说明。
9. 编造不存在的代码示例。
10. 将内部调用标记为官方示例。
11. 跳过失败测试。
12. 删除不容易通过的验收项。
13. 降低验证等级来完成构建。
14. 只完成项目骨架后宣布完成。
15. 将 V1 必需工作改写成“未来计划”后宣布完成。
16. 使用大量核心 TODO、`NotImplementedError` 或空实现伪装完整接口。
17. 在未满足 Definition of Done 时宣布目标完成。

------

# 20. 最终架构结论

V1 固定采用：

```text
固定 JUCE commit
+ 锁定 Doxygen 版本
+ JUCE 官方 Doxygen XML
+ XML Schema 校验
+ Canonical IR
+ 类型级 Markdown
+ 成员级稳定锚点
+ 官方仓库指南
+ 纯文本符号索引
+ 可重建 FTS5
+ JUCE 官方示例索引
+ JUCE 源码位置索引
+ 固定 Agent 查询协议
+ Fail-closed 验证
+ 自动进度恢复
+ 原子版本发布
+ 单一机器验收入口
```

项目完成后的参考系统必须形成以下明确分工：

```text
Markdown 解释 API
官方示例展示用法
同版本源码确认事实
索引负责定位
版本锁保证一致
验证阻止静默损坏
自动执行协议保证 Agent 持续完成全部 V1
```

本项目不存在“基本完成”或“部分完成即成功”的状态。

只有全部 V1 Definition of Done 满足、统一机器验收返回退出码 `0`、Git 工作区干净且不存在外部阻断文件时，Goal 才算完成。
# JUCE Agent Reference Implementation Specification

## 1. 文档地位

本文档定义 `plan.md` 的具体实施规范，包括：

- 技术选型
- 仓库结构
- 模块职责
- 数据模型
- CLI 契约
- 构建流程
- 测试策略
- 自动恢复协议
- Git 提交规则
- 最终机器验收

文档优先级如下：

```text
AGENTS.md
    ↓ 执行控制、恢复和停止规则

plan.md
    ↓ 目标、架构、范围和 Definition of Done

implementation.md
    ↓ 具体实现、测试、命令和提交顺序
```

执行 Agent 必须同时遵守三份文档。

如本文档的某项实现细节与 `plan.md` 的架构或范围冲突，以 `plan.md` 为准；Agent 必须通过兼容性实现修正冲突，不得自行降低目标。

------

# 2. 自动执行目标

本项目必须支持 Agent 使用 Goal 功能，从仓库初始状态持续执行到 V1 完整交付。

Agent 不得只完成以下部分后停止：

- 项目骨架
- Doxygen 调用
- XML Parser 雏形
- 部分 Markdown 页面
- 部分 CLI
- 仅单元测试通过
- 仅生成演示 fixture
- 仅提交计划或报告

只有满足以下条件，才允许声明完成：

```text
所有 Phase 完成
+ 所有测试通过
+ lint 通过
+ 类型检查通过
+ 真实 JUCE smoke test 通过
+ 搜索质量测试通过
+ 确定性测试通过
+ 输出完整性验证通过
+ juce-doc verify 通过
+ 最终统一验收命令返回 0
+ Git 工作区干净
+ 无 blocker 文件
+ 无核心 TODO 或占位实现
```

普通实现困难、测试失败或真实 JUCE XML 中出现新节点，均不构成停止理由。

------

# 3. V1 技术选型

## 3.1 编程语言

使用：

```text
Python 3.12+
```

原因：

- XML 解析工具成熟
- Markdown、JSONL、TSV 和 SQLite 处理方便
- Windows、Linux 和 macOS 均可运行
- 易于编写 fixture 和 golden test
- 适合编程 Agent 维护
- 不需要复杂编译工具链即可运行核心功能

## 3.2 项目和依赖管理

优先使用：

```text
uv
```

但项目不得硬依赖只有 `uv` 才能运行。

必须同时支持：

```powershell
python -m venv .venv
python -m pip install -e ".[dev]"
```

## 3.3 核心依赖

`pyproject.toml` 建议范围：

```toml
[project]
requires-python = ">=3.12"

dependencies = [
    "lxml>=5,<7",
    "typer>=0.16,<1",
    "rich>=14,<15",
    "platformdirs>=4,<5",
    "pyyaml>=6,<7"
]

[project.optional-dependencies]
dev = [
    "pytest>=8,<9",
    "pytest-cov>=6,<8",
    "ruff>=0.12,<1",
    "mypy>=1.17,<2"
]
```

除非真实兼容性测试证明有必要，不得随意增加大型依赖。

## 3.4 标准库能力

应优先使用标准库：

- `dataclasses`
- `pathlib`
- `subprocess`
- `sqlite3`
- `json`
- `hashlib`
- `shutil`
- `tempfile`
- `re`
- `typing`
- `xml` 仅用于辅助，不替代 `lxml` Schema 校验

## 3.5 V1 不引入

V1 核心实现不得依赖：

- Clang Python bindings
- libclang
- Tree-sitter
- 向量数据库
- embedding API
- MCP Server
- HTTP Server
- Web UI
- 网络爬虫
- LLM API

可预留 Provider 接口，但不得留下核心空实现或让延期能力阻塞 V1。

------

# 4. 仓库初始结构

执行 Agent 应创建：

```text
juce-agent-reference/
├─ AGENTS.md
├─ plan.md
├─ implementation.md
├─ README.md
├─ pyproject.toml
├─ toolchain.lock.json
├─ .gitignore
│
├─ src/
│  └─ juce_reference/
│     ├─ __init__.py
│     ├─ __main__.py
│     ├─ cli.py
│     ├─ errors.py
│     ├─ config.py
│     ├─ logging.py
│     ├─ build_context.py
│     ├─ source.py
│     ├─ doctor.py
│     ├─ doxygen_runner.py
│     ├─ xml_validator.py
│     ├─ xml_parser.py
│     ├─ documentation_nodes.py
│     ├─ model.py
│     ├─ path_mapper.py
│     ├─ markdown_renderer.py
│     ├─ repository_docs.py
│     ├─ alias_loader.py
│     ├─ example_scanner.py
│     ├─ source_indexer.py
│     ├─ index_builder.py
│     ├─ search.py
│     ├─ output_validator.py
│     ├─ smoke_test.py
│     ├─ determinism.py
│     ├─ publisher.py
│     ├─ progress.py
│     └─ util/
│        ├─ command.py
│        ├─ hashing.py
│        ├─ json_io.py
│        ├─ markdown.py
│        ├─ paths.py
│        └─ text.py
│
├─ config/
│  └─ aliases.yml
│
├─ scripts/
│  ├─ bootstrap.ps1
│  ├─ bootstrap.sh
│  ├─ goal-check.ps1
│  └─ goal-check.sh
│
├─ tests/
│  ├─ fixtures/
│  │  ├─ doxygen/
│  │  ├─ repository/
│  │  ├─ examples/
│  │  └─ search/
│  ├─ golden/
│  ├─ integration/
│  ├─ test_alias_loader.py
│  ├─ test_doctor.py
│  ├─ test_doxygen_runner.py
│  ├─ test_xml_validator.py
│  ├─ test_xml_parser.py
│  ├─ test_path_mapper.py
│  ├─ test_markdown_renderer.py
│  ├─ test_repository_docs.py
│  ├─ test_example_scanner.py
│  ├─ test_source_indexer.py
│  ├─ test_index_builder.py
│  ├─ test_search.py
│  ├─ test_output_validator.py
│  ├─ test_publisher.py
│  └─ test_determinism.py
│
└─ .agent/
   ├─ progress.json
   └─ README.md
```

`.gitignore` 至少包含：

```gitignore
.venv/
.build/
dist/
*.egg-info/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.agent/blocker.json
```

`.agent/progress.json` 应提交初始 Schema，但运行中的临时错误详情是否提交由 `AGENTS.md` 规定。推荐提交该文件，使中断恢复信息可以保留。

------

# 5. 工具链锁定

根目录创建：

```text
toolchain.lock.json
```

建议结构：

```json
{
  "schema_version": 1,
  "python": {
    "minimum": "3.12"
  },
  "doxygen": {
    "version": "<exact-version>"
  },
  "generator": {
    "version": "0.1.0"
  },
  "schemas": {
    "ir": 1,
    "markdown": 1,
    "index": 1,
    "progress": 1
  }
}
```

Doxygen 版本必须是环境中实际验证可用的精确版本。

Agent 初始化时应：

1. 执行 `doxygen --version`
2. 若 lock 文件已有版本，严格匹配
3. 若 lock 文件尚未填写，在环境验证后写入实际版本
4. 写入后不得在后续阶段自动漂移
5. 如确需升级，必须：
   - 更新 lock
   - 更新测试 fixture
   - 运行全量回归
   - 说明升级原因

不得在代码中写死 Doxygen 版本。

------

# 6. 命令行接口

命令入口：

```powershell
juce-doc
```

同时必须支持：

```powershell
python -m juce_reference
```

## 6.1 必须提供的命令

```text
juce-doc doctor
juce-doc generate
juce-doc validate
juce-doc verify
juce-doc symbol
juce-doc search
juce-doc show
juce-doc examples
juce-doc source
juce-doc related
juce-doc rebuild-index
juce-doc smoke
juce-doc determinism
juce-doc test
juce-doc all
```

## 6.2 通用输出

所有查询类命令支持：

```text
--json
```

所有构建类命令支持：

```text
--verbose
--no-color
```

CLI 默认：

- 人类可读输出写 stdout
- 错误写 stderr
- 成功返回 0
- 失败返回稳定退出码
- JSON 模式不得混入 Rich 格式文本

------

# 7. 退出码

统一定义：

| 退出码 | 含义                         |
| ------ | ---------------------------- |
| 0      | 成功                         |
| 2      | 参数或输入错误               |
| 3      | 环境检查失败                 |
| 4      | JUCE checkout 校验失败       |
| 5      | Doxygen 执行失败             |
| 6      | XML Schema 或 XML 完整性失败 |
| 7      | XML 转 IR 失败               |
| 8      | Markdown 或索引生成失败      |
| 9      | 输出验证失败                 |
| 10     | Smoke test 失败              |
| 11     | 搜索质量测试失败             |
| 12     | 确定性测试失败               |
| 13     | 发布失败                     |
| 14     | 版本 verify 失败             |
| 15     | Git 工作区最终状态失败       |
| 20     | 不可恢复外部阻断             |

退出码必须集中定义，不得散落魔法数字。

------

# 8. 统一异常模型

`errors.py`：

```python
class JuceReferenceError(Exception):
    exit_code: int = 1

class CliUsageError(JuceReferenceError):
    exit_code = 2

class EnvironmentCheckError(JuceReferenceError):
    exit_code = 3

class JuceSourceError(JuceReferenceError):
    exit_code = 4

class DoxygenExecutionError(JuceReferenceError):
    exit_code = 5

class XmlValidationError(JuceReferenceError):
    exit_code = 6

class ConversionError(JuceReferenceError):
    exit_code = 7

class GenerationError(JuceReferenceError):
    exit_code = 8

class OutputValidationError(JuceReferenceError):
    exit_code = 9

class SmokeTestError(JuceReferenceError):
    exit_code = 10

class SearchQualityError(JuceReferenceError):
    exit_code = 11

class DeterminismError(JuceReferenceError):
    exit_code = 12

class PublishError(JuceReferenceError):
    exit_code = 13

class VersionVerificationError(JuceReferenceError):
    exit_code = 14

class RepositoryStateError(JuceReferenceError):
    exit_code = 15

class ExternalBlockerError(JuceReferenceError):
    exit_code = 20
```

只有 CLI 层允许：

```python
raise typer.Exit(...)
```

核心模块必须抛出领域异常。

错误对象应尽量携带：

- 阶段
- 命令
- 文件路径
- XML tag
- compound refid
- member refid
- symbol
- 原始异常
- 建议修复动作

------

# 9. 配置模型

`config.py` 应定义不可变配置对象。

```python
@dataclass(frozen=True)
class GeneratorConfig:
    juce_root: Path
    output_root: Path
    allow_dirty: bool
    keep_build: bool
    release: bool
    aliases_file: Path
    strict_external_links: bool
```

配置来源优先级：

```text
CLI 参数
> 环境变量
> 项目配置文件
> 默认值
```

推荐支持可选配置：

```text
juce-reference.toml
```

但 V1 不要求复杂配置系统。核心命令必须只依靠 CLI 参数即可运行。

------

# 10. BuildContext

`build_context.py`：

```python
@dataclass(frozen=True)
class BuildContext:
    build_id: str
    repository_root: Path
    juce_root: Path
    output_root: Path
    build_root: Path
    release_root: Path
    juce_commit: str
    juce_dirty: bool
    doxygen_version: str
    generator_version: str
    ir_schema_version: int
    markdown_schema_version: int
    index_schema_version: int
```

要求：

- 构建开始时创建一次
- 后续显式传入模块
- 不允许模块重新读取环境推断这些值
- `build_id` 可以用于临时目录，但不得进入正式确定性输出
- 临时目录使用绝对路径
- 正式索引路径使用规范化相对路径

------

# 11. 环境检查：`doctor`

`doctor.py` 实现环境检查。

命令：

```powershell
juce-doc doctor --juce-root D:\SDK\JUCE
```

必须检查：

## 11.1 Python

- Python ≥ 3.12
- 当前解释器可导入全部依赖
- 当前虚拟环境路径可写

## 11.2 Git

- `git --version` 成功
- 指定 JUCE checkout 可以运行 Git 命令

## 11.3 Doxygen

- `doxygen --version` 成功
- 与 `toolchain.lock.json` 完全一致

## 11.4 SQLite

验证：

```python
sqlite3.connect(":memory:").execute(
    "CREATE VIRTUAL TABLE test USING fts5(content)"
)
```

若环境缺少 FTS5，必须失败，而不是默默降级。

## 11.5 文件系统

- 构建目录可写
- 输出目录父目录可写
- 可以执行原子重命名测试
- Windows 下路径长度满足需要，或明确检测长路径风险

## 11.6 JUCE 结构

至少存在：

```text
modules/
docs/doxygen/Doxyfile
```

`examples/` 可以缺失，但 V1 正式真实 JUCE smoke test 应要求官方完整 checkout 中存在。

## 11.7 Git 状态

- 能读取完整 40 位 SHA
- 默认要求 clean
- `--allow-dirty` 时明确警告
- submodule 或 sparse checkout 情况必须记录

`doctor` 必须输出结构化报告。

------

# 12. JUCE Source 校验

`source.py`：

```python
@dataclass(frozen=True)
class JuceSource:
    root: Path
    git_root: Path
    commit: str
    dirty: bool
    modules_dir: Path
    docs_dir: Path
    doxygen_dir: Path
    doxygen_file: Path
    examples_dir: Path | None
    extras_dir: Path | None
```

实现要求：

1. 所有 Git 命令使用参数数组

2. 不使用 `shell=True`

3. 处理路径中空格

4. 验证 Git 根目录与 JUCE 根目录关系

5. 获取完整 SHA：

   ```text
   git rev-parse HEAD
   ```

6. 检查工作区：

   ```text
   git status --porcelain=v1 --untracked-files=normal
   ```

7. 若 dirty 且未允许，失败

8. 不修改 JUCE checkout

9. 不运行会改变 checkout 的命令

------

# 13. Doxygen Runner

`doxygen_runner.py`：

```python
@dataclass(frozen=True)
class DoxygenResult:
    xml_dir: Path
    generated_doxyfile: Path
    warnings_file: Path
    stdout_file: Path
    stderr_file: Path
```

## 13.1 官方 Doxyfile Overlay

不得修改：

```text
JUCE/docs/doxygen/Doxyfile
```

流程：

1. 读取官方 Doxyfile
2. 写入 `.build/<build-id>/Doxyfile.generated`
3. 在末尾追加覆盖项
4. 从 `JUCE/docs/doxygen` 作为 cwd 运行
5. 输出到临时构建目录

覆盖配置：

```text
OUTPUT_DIRECTORY   = <absolute-build-output>
PROJECT_NUMBER     = <full-commit>
GENERATE_HTML      = NO
GENERATE_XML       = YES
XML_PROGRAMLISTING = NO
WARN_LOGFILE       = <absolute-warning-file>
TIMESTAMP          = NO
```

如果官方 Doxyfile 已设置同名选项，后追加值作为最终覆盖。

## 13.2 Doxygen 执行

必须：

- 捕获 stdout
- 捕获 stderr
- 保存命令
- 保存版本
- 检查退出码
- 检查预期文件

成功后必须存在：

```text
xml/index.xml
xml/index.xsd
xml/compound.xsd
```

不能只依赖退出码判断成功。

## 13.3 Warning 处理

Doxygen warning 不自动导致失败，但必须：

- 保存完整日志
- 分类统计
- 对可能导致内容缺失的 warning 升级为失败
- 普通 warning 写入报告

例如以下 warning 应考虑失败：

- XML 输出文件无法写入
- 输入文件无法读取
- 引用目标严重缺失
- 解析错误导致实体跳过

------

# 14. XML Schema 校验

`xml_validator.py`：

```python
@dataclass(frozen=True)
class XmlValidationIssue:
    file: str
    line: int | None
    message: str

@dataclass(frozen=True)
class XmlValidationReport:
    index_valid: bool
    compound_count: int
    valid_compound_count: int
    issues: tuple[XmlValidationIssue, ...]
```

流程：

1. 使用 `index.xsd` 校验 `index.xml`
2. 读取 index compound 列表
3. 检查每个 `<refid>.xml`
4. 使用 `compound.xsd` 校验 compound
5. 检查重复 compound refid
6. 检查 index 中 member refid 重复
7. 输出统计

Schema 校验失败后不得继续转换。

为避免真实 JUCE 全量校验过慢，可以缓存已校验文件 hash，但首版实现以正确性优先。

------

# 15. Canonical IR

## 15.1 设计原则

IR 必须：

- 与 Markdown 格式解耦
- 保留 API 语义
- 保留原始顺序
- 支持确定性排序
- 可被测试 fixture 构造
- 不暴露 `lxml` 节点到 Renderer

所有 dataclass 推荐：

```python
@dataclass(frozen=True, slots=True)
```

## 15.2 SourceLocation

```python
@dataclass(frozen=True, slots=True)
class SourceLocation:
    file: str
    line: int | None = None
    column: int | None = None
    body_file: str | None = None
    body_start: int | None = None
    body_end: int | None = None
```

## 15.3 Reference

```python
@dataclass(frozen=True, slots=True)
class Reference:
    text: str
    refid: str | None = None
    external_url: str | None = None
    kind: str | None = None
```

内部 `refid` 和外部 URL 不能混为一个字符串字段。

## 15.4 Parameter

```python
@dataclass(frozen=True, slots=True)
class Parameter:
    type_nodes: tuple["DocNode", ...]
    name: str | None
    default_value_nodes: tuple["DocNode", ...]
    description: tuple["DocNode", ...]
```

不能仅保存扁平字符串，否则模板引用和链接会丢失。

## 15.5 Member

```python
@dataclass(frozen=True, slots=True)
class Member:
    refid: str
    kind: str
    name: str
    qualified_name: str
    definition_nodes: tuple["DocNode", ...]
    args_string_nodes: tuple["DocNode", ...]
    signature: str
    access: str
    static: bool
    const: bool
    explicit: bool
    inline: bool
    mutable: bool
    virtual_kind: str | None
    parameters: tuple[Parameter, ...]
    template_parameters: tuple[Parameter, ...]
    brief: tuple["DocNode", ...]
    details: tuple["DocNode", ...]
    location: SourceLocation | None
    deprecated: bool
    documented: bool
```

## 15.6 Compound

```python
@dataclass(frozen=True, slots=True)
class Compound:
    refid: str
    kind: str
    name: str
    qualified_name: str
    title: str | None
    brief: tuple["DocNode", ...]
    details: tuple["DocNode", ...]
    bases: tuple[Reference, ...]
    derived: tuple[Reference, ...]
    inner_compounds: tuple[Reference, ...]
    members: tuple[Member, ...]
    location: SourceLocation | None
    module: str | None
    documented: bool
```

## 15.7 处理状态

每个实体必须记录：

```python
class EntityDisposition(str, Enum):
    RENDERED = "rendered"
    INDEXED_ONLY = "indexed-only"
    SKIPPED_WITH_REASON = "skipped-with-reason"
```

跳过时必须有稳定 reason code，例如：

```text
private-member
anonymous-internal
unsupported-non-public-file-detail
duplicate-generated-artifact
```

------

# 16. 文档节点

`documentation_nodes.py` 至少实现：

```python
class DocNode: ...

@dataclass(frozen=True, slots=True)
class Text(DocNode):
    value: str

@dataclass(frozen=True, slots=True)
class Paragraph(DocNode):
    children: tuple[DocNode, ...]

@dataclass(frozen=True, slots=True)
class InlineCode(DocNode):
    value: str

@dataclass(frozen=True, slots=True)
class CodeBlock(DocNode):
    code: str
    language: str | None

@dataclass(frozen=True, slots=True)
class ReferenceNode(DocNode):
    reference: Reference
    children: tuple[DocNode, ...]

@dataclass(frozen=True, slots=True)
class UnorderedList(DocNode):
    items: tuple["ListItem", ...]

@dataclass(frozen=True, slots=True)
class OrderedList(DocNode):
    items: tuple["ListItem", ...]

@dataclass(frozen=True, slots=True)
class ListItem(DocNode):
    children: tuple[DocNode, ...]

@dataclass(frozen=True, slots=True)
class Table(DocNode):
    rows: tuple["TableRow", ...]

@dataclass(frozen=True, slots=True)
class TableRow(DocNode):
    cells: tuple["TableCell", ...]
    header: bool

@dataclass(frozen=True, slots=True)
class TableCell(DocNode):
    children: tuple[DocNode, ...]

@dataclass(frozen=True, slots=True)
class Section(DocNode):
    level: int
    title: tuple[DocNode, ...]
    children: tuple[DocNode, ...]

@dataclass(frozen=True, slots=True)
class Note(DocNode):
    children: tuple[DocNode, ...]

@dataclass(frozen=True, slots=True)
class WarningNode(DocNode):
    children: tuple[DocNode, ...]

@dataclass(frozen=True, slots=True)
class DeprecatedNode(DocNode):
    children: tuple[DocNode, ...]

@dataclass(frozen=True, slots=True)
class ParameterList(DocNode):
    kind: str
    entries: tuple["ParameterEntry", ...]

@dataclass(frozen=True, slots=True)
class Formula(DocNode):
    value: str
    display: bool

@dataclass(frozen=True, slots=True)
class ImageNode(DocNode):
    name: str
    caption: tuple[DocNode, ...]
    external_url: str | None

@dataclass(frozen=True, slots=True)
class LineBreak(DocNode):
    pass
```

------

# 17. 未知 XML 节点策略

不能采用统一“未知节点全部失败”，也不能统一 `.itertext()` 忽略结构。

## 17.1 必须失败

未知节点涉及以下语义时：

- API 签名
- 参数类型
- 默认值
- 内部引用
- 代码块内容
- 枚举值
- 模板参数
- 成员关系
- deprecated
- return
- throws
- source location

抛出：

```python
UnsupportedSemanticNodeError
```

错误应包含：

- XML tag
- XML 文件
- line
- compound refid
- member refid
- 父节点路径

## 17.2 可降级

仅影响纯展示时可以：

- 递归保留文本
- 记录 `formatting-warnings.json`
- 使用稳定 warning code

例如：

```text
unsupported-inline-style
unsupported-layout-container
unsupported-nonsemantic-decoration
```

## 17.3 新节点修复流程

Agent 遇到真实新节点必须：

1. 提取最小 XML fixture
2. 添加失败测试
3. 判断节点是否语义性
4. 扩展 IR
5. 扩展 Parser
6. 扩展 Renderer
7. 运行局部测试
8. 运行全量 parser/renderer 测试
9. 继续执行

不得要求用户决定普通节点如何实现。

------

# 18. XML Parser

`xml_parser.py` 分两阶段。

## 18.1 Index Parser

```python
@dataclass(frozen=True, slots=True)
class CompoundIndexEntry:
    refid: str
    kind: str
    name: str
    member_refids: tuple[str, ...]
```

必须保留 index 顺序用于诊断，但正式输出采用确定性排序。

## 18.2 Compound Parser

解析：

- compounddef
- compoundname
- title
- briefdescription
- detaileddescription
- basecompoundref
- derivedcompoundref
- innerclass
- innernamespace
- sectiondef
- memberdef
- location
- templateparamlist

## 18.3 Member Parser

至少支持：

- function
- variable
- typedef
- enum
- enumvalue
- define
- property
- friend

成员过滤依据：

- private 默认不渲染
- protected 保留
- public 保留
- package 依据实际 Doxygen kind 处理
- internal entity 根据官方标记降低或排除

## 18.4 签名构建

优先使用 Doxygen 提供字段组合成稳定签名，但不得丢失：

- 返回类型
- qualified name
- 模板参数
- 参数类型
- 参数名
- 默认值
- `const`
- `volatile`
- ref qualifier
- `noexcept`
- `override`
- `final`
- pure virtual

若 XML 无法提供某个限定符，测试必须明确当前边界，不能编造。

------

# 19. 文档代码块

必须专门区分：

```text
文档注释代码块
完整源码 listing
inline code
声明代码
```

`XML_PROGRAMLISTING = NO` 时，文档代码块仍必须保留。

## 19.1 Fixture

必须包含：

```cpp
/**
    Example:

    \code
    Foo foo;
    foo.start();
    \endcode
*/
class Foo {};
```

输出：

~~~markdown
```cpp
Foo foo;
foo.start();
```
~~~

## 19.2 代码块语言

规则：

- Doxygen 明确标识 C++：`cpp`
- 文档上下文可明确为 C++：允许 `cpp`
- 无法确定：`text`
- 不得将 shell、CMake 或其他语言误标为 C++

## 19.3 完整源码排除

普通实现：

```cpp
void Foo::start()
{
    internalImplementation();
}
```

不得因为 API 文档生成而进入 Markdown。

Agent 应通过 source 查询定位该实现。

------

# 20. Path Mapper

`path_mapper.py` 必须在渲染前为所有 compound 和 member 分配目标。

## 20.1 Compound 路径

```text
juce::AudioProcessor
→ reference/types/juce/AudioProcessor.md
juce::dsp::ProcessorChain
→ reference/types/juce/dsp/ProcessorChain.md
```

模块：

```text
juce_audio_processors
→ reference/modules/juce_audio_processors.md
```

命名空间：

```text
juce::dsp
→ reference/namespaces/juce/dsp.md
```

## 20.2 路径清理

必须处理：

- Windows 非法字符
- Windows 保留文件名
- 空名称
- 匿名实体
- 大小写冲突
- 清理后冲突
- 超长单文件名

## 20.3 冲突检测

使用：

```python
path.as_posix().casefold()
```

作为最低限度的 Windows 冲突键。

冲突时追加：

```text
--<sha256(refid) 前 8 位>
```

## 20.4 成员锚点

```text
m-<sha256(member_refid) 前 10 位>
```

要求：

- 稳定
- ASCII
- 不受名称变化影响
- 不受 Markdown renderer 影响
- 重载不冲突

## 20.5 PathMap

```python
@dataclass(frozen=True)
class OutputTarget:
    refid: str
    path: str
    anchor: str | None

@dataclass(frozen=True)
class PathMap:
    compounds: Mapping[str, OutputTarget]
    members: Mapping[str, OutputTarget]
```

Renderer 只能使用 `PathMap`，不得自行重新计算路径。

------

# 21. Markdown Renderer

`markdown_renderer.py`：

```python
@dataclass(frozen=True)
class RenderedDocument:
    path: str
    content: str
    symbols: tuple[str, ...]
    anchors: tuple[str, ...]
```

## 21.1 页面结构

类型页面固定顺序：

1. Frontmatter
2. 标题
3. Brief
4. Quick reference
5. Declaration
6. Inheritance
7. Detailed description
8. Member index
9. Public member details
10. Protected member details
11. Related symbols
12. Official examples
13. Source

模块页面：

1. Frontmatter
2. 模块标题
3. 模块说明
4. 主要类型
5. 函数、枚举和宏
6. 相关模块
7. Source

命名空间页面：

1. Frontmatter
2. 说明
3. 内部 namespace
4. 类型
5. 自由函数
6. enums 和 aliases

## 21.2 Frontmatter

示例：

```yaml
---
symbol: juce::AudioProcessor
short_name: AudioProcessor
kind: class
module: juce_audio_processors
header: processors/juce_AudioProcessor.h
doxygen_id: classjuce_1_1AudioProcessor
juce_commit: <full-sha>
documented: true
---
```

YAML 字符串必须正确转义。

## 21.3 Brief 和 details 去重

仅当规范化文本和节点结构完全等价时去重。

不得使用语义相似度或 LLM 判断。

## 21.4 内部链接

所有 `refid` 通过 `PathMap` 转相对链接。

无法解析的内部引用必须失败。

外部链接保持 URL。

## 21.5 Markdown 稳定规则

- UTF-8
- LF
- 文件末尾一个换行
- ATX 标题
- fenced code
- 显式成员锚点
- POSIX 相对路径
- 不写生成时间
- 固定字段顺序
- 固定成员排序策略

------

# 22. Repository Markdown 导入

`repository_docs.py` 导入：

```text
JUCE/docs/*.md
JUCE/README.md
JUCE/BREAKING_CHANGES.md
```

## 22.1 处理规则

- 保留原文
- 添加最小 frontmatter
- 保留原始标题
- 修复明确可解析的相对链接
- 保留外部链接
- 不翻译
- 不总结
- 不修改技术表述

## 22.2 内部链接

仓库 Markdown 内链接到：

- 其他 `.md`
- JUCE 源文件
- 图片
- docs 子目录

必须转换为参考库可用路径或指向 JUCE checkout 的相对路径。

无法解析的仓库内链接必须失败。

## 22.3 图片

V1 不要求下载远程图片。

本地仓库图片可以：

- 复制到 `guides/assets/`
- 或通过稳定相对路径引用原 JUCE checkout

选择一种并全局一致。

------

# 23. 别名配置

`config/aliases.yml`：

```yaml
juce::AudioProcessorValueTreeState:
  aliases:
    - APVTS
    - plugin parameter state
    - parameter state
  concepts:
    - save plugin parameter state
    - restore plugin parameter state

juce::SmoothedValue:
  aliases:
    - parameter smoothing
  concepts:
    - smooth parameter changes
    - avoid parameter zipper noise

juce::dsp::ProcessorChain:
  aliases:
    - DSP chain
    - processor pipeline
```

`alias_loader.py` 必须：

- 校验 YAML Schema
- 去重
- 规范化空白
- 保留人工顺序
- 验证 symbol 存在
- 未知 symbol 导致构建失败

自动别名：

```text
AudioProcessorValueTreeState
Audio Processor Value Tree State
audio processor value tree state
```

自动缩写为低权重，不得覆盖人工别名。

------

# 24. Symbol Index

`index_builder.py`：

```python
@dataclass(frozen=True)
class SymbolRecord:
    symbol: str
    short_name: str
    owner: str | None
    kind: str
    access: str | None
    module: str | None
    documentation_path: str
    anchor: str | None
    signature: str | None
    brief_text: str
    aliases: tuple[str, ...]
    concepts: tuple[str, ...]
    declaration: SourceLocation | None
    definition: SourceLocation | None
    documented: bool
    internal: bool
```

## 24.1 输出文件

```text
index/symbols.tsv
index/symbols.jsonl
index/relationships.jsonl
index/source-locations.jsonl
```

## 24.2 TSV

列顺序固定：

```text
qualified_name
short_name
owner
kind
access
module
documentation_path
anchor
signature
documented
brief
```

必须正确转义 tab 和换行。

## 24.3 JSONL

每行一个对象，固定 key 顺序。

## 24.4 排序

固定：

```text
symbol.casefold()
kind
signature or ""
documentation_path
anchor or ""
```

## 24.5 Module 推断

优先级：

1. Doxygen group
2. `modules/<module>/...`
3. null

不得依据类名猜测。

------

# 25. Relationships Index

记录关系类型：

```text
base-of
derived-from
member-of
contains
namespace-of
module-of
references
referenced-by
example-uses-symbol
source-declaration
source-definition
```

每条关系：

```json
{
  "type": "derived-from",
  "source": "juce::AudioPluginInstance",
  "target": "juce::AudioProcessor",
  "source_refid": "...",
  "target_refid": "...",
  "confidence": "doxygen"
}
```

关系输出必须稳定排序。

------

# 26. Example Scanner

`example_scanner.py` 第一版扫描：

```text
JUCE/examples
```

## 26.1 文件类型

扫描：

- `.h`
- `.hpp`
- `.cpp`
- `.cc`
- `.cxx`
- `.mm`
- `.m`
- `.inl`
- `CMakeLists.txt`
- `.jucer`
- `.md`

## 26.2 示例单位

示例单位优先为：

- 子目录
- 明确 demo 文件
- 顶层示例文件

示例名称必须稳定，不依赖绝对路径。

## 26.3 分类

根据路径和项目结构归类：

```text
plugins
dsp
audio
gui
midi
utilities
other
```

## 26.4 符号关联

V1 只建立确定性关联：

1. 完整限定名：

   ```cpp
   juce::AudioProcessorValueTreeState
   ```

2. `juce::<KnownSymbol>`

3. 明确继承：

   ```cpp
   class X : public juce::AudioProcessor
   ```

4. 已知完整 namespace 链文本

不得将任意短名称出现视为高置信度。

## 26.5 关联记录

```python
@dataclass(frozen=True)
class ExampleSymbolUse:
    example_name: str
    category: str
    file: str
    line: int
    symbol: str
    confidence: str
```

V1 confidence：

```text
qualified-text
qualified-inheritance
qualified-template
```

## 26.6 示例页面

生成：

```text
examples/INDEX.md
examples/plugins.md
examples/dsp.md
examples/audio.md
examples/gui.md
examples/midi.md
examples/utilities.md
examples/other.md
```

只提供导航和相关 API，不复制完整源码。

------

# 27. Source Indexer

`source_indexer.py` 使用 Doxygen location。

## 27.1 声明

使用：

- file
- line
- column

confidence：

```text
doxygen-location
```

## 27.2 实现

使用：

- body_file
- body_start
- body_end

confidence：

```text
doxygen-body-location
```

## 27.3 禁止猜测

若无可靠 body location：

```json
"definition": null
```

CLI 输出：

```text
Definition not resolved
```

不得通过正则匹配函数名猜行号。

## 27.4 路径验证

所有路径必须：

- 在 JUCE root 内
- 文件存在
- 行号大于 0
- 行号不超过合理范围

------

# 28. SQLite FTS5

`search.sqlite` 是缓存。

## 28.1 表

普通表：

```sql
symbols
relationships
examples
metadata
```

FTS 表：

```sql
symbol_fts
```

建议字段：

```text
symbol
short_name
aliases
concepts
kind
module
signature
brief
body
example_names
documentation_path
anchor
```

## 28.2 重建

必须提供：

```powershell
juce-doc rebuild-index --reference <path>
```

输入仅依赖：

- Markdown
- JSONL
- aliases 已固化数据
- manifest

删除 SQLite 后必须可完整重建。

## 28.3 搜索排序

优先级：

```text
完整限定名精确匹配
> 短名称精确匹配
> 人工别名精确匹配
> 完整名称前缀
> CamelCase 分词
> 签名
> concepts
> brief
> 示例名称
> 正文
```

同分排序：

```text
公开已文档化
> 公开未文档化
> protected
> internal
```

再按：

```text
symbol.casefold()
kind
documentation_path
anchor
```

## 28.4 查询安全

使用 SQL 参数绑定。

不得直接拼接用户输入。

------

# 29. 查询命令

## 29.1 `symbol`

```powershell
juce-doc symbol "juce::AudioProcessor"
```

行为：

- 精确 symbol 优先
- 短名称匹配
- 多个结果时按排序展示
- `--json` 输出结构化结果

## 29.2 `show`

```powershell
juce-doc show "juce::AudioProcessor::processBlock"
```

输出：

- symbol
- signature
- owner
- module
- Markdown path
- anchor
- brief
- declaration
- examples

可选：

```text
--print-content
```

打印相关 Markdown section，但默认只返回定位信息，避免上下文过大。

## 29.3 `search`

```powershell
juce-doc search "save plugin parameter state"
```

支持：

```text
--limit
--kind
--module
--public-only
--json
```

## 29.4 `examples`

```powershell
juce-doc examples "juce::SmoothedValue"
```

结果按：

```text
official example
> documentation snippet
> internal usage
```

V1 主要返回 official examples 和文档代码块。

## 29.5 `source`

```powershell
juce-doc source "juce::Component::repaint"
```

输出声明、定义和置信度。

## 29.6 `related`

输出：

- bases
- derived
- member owner
- module
- referenced symbols
- examples

------

# 30. 输出验证器

`output_validator.py`：

```python
@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    code: str
    message: str
    path: str | None
    symbol: str | None

@dataclass(frozen=True)
class ValidationReport:
    passed: bool
    issues: tuple[ValidationIssue, ...]
    statistics: Mapping[str, int]
```

## 30.1 路径验证

- 路径唯一
- casefold 后唯一
- 无 Windows 保留名
- 无 `..` 逃逸
- 无绝对路径泄漏到正式索引
- 正式路径均使用 `/`

## 30.2 Markdown 验证

- 文件存在
- 标题存在
- Frontmatter 有效
- fenced code block 闭合
- 内部链接目标存在
- anchor 存在
- 无 `unresolved://`
- 无指向 Doxygen HTML 的内部链接

## 30.3 索引验证

- 每个 documentation path 存在
- 每个 anchor 存在
- 每个 source path 存在
- 每个 example path 存在
- alias symbol 存在
- manifest 与文件集合一致

## 30.4 覆盖率验证

每个 compound：

```text
rendered
indexed-only
skipped-with-reason
```

每个 member：

```text
rendered-in-owner
indexed-only
skipped-with-reason
```

统计必须写入报告。

禁止未计数丢弃。

## 30.5 API 语义验证

fixture 必须检查：

- 参数顺序
- 默认参数
- 模板参数
- `const`
- `noexcept`
- `override`
- pure virtual
- enum values
- deprecated
- note
- warning
- return
- throws
- 文档代码块

------

# 31. Manifest 和 Lock

## 31.1 `docs.lock.json`

```json
{
  "schema_version": 1,
  "juce": {
    "commit": "<full-sha>",
    "dirty": false
  },
  "toolchain": {
    "python": "3.12.x",
    "doxygen": "<exact>",
    "generator": "0.1.0"
  },
  "schemas": {
    "ir": 1,
    "markdown": 1,
    "index": 1
  }
}
```

正式 clean release 不写绝对路径。

## 31.2 `manifest.json`

至少包含：

- 版本
- documents
- symbols statistics
- examples statistics
- skipped entities statistics
- 文件 hashes

正式 manifest 不写当前时间。

审计时间可写入非确定性报告：

```text
reports/generation.json
```

------

# 32. 发布器

`publisher.py` 输出：

```text
<output>/
├─ current.json
└─ releases/
   └─ <full-commit>/
```

## 32.1 发布过程

1. 生成到 `.build/<build-id>/candidate`
2. 运行完整验证
3. 计算内容 hash
4. 如果 release 不存在，原子 rename
5. 如果已存在：
   - hash 相同：复用
   - hash 不同：失败
6. 原子替换 `current.json`

## 32.2 Dirty 构建

dirty 构建：

- 可生成到临时目录
- 可用于本地调试
- 不允许写入正式 `releases/<commit>`
- 不允许更新 `current.json`

## 32.3 Windows

不依赖符号链接。

`current.json`：

```json
{
  "commit": "<full-sha>",
  "path": "releases/<full-sha>"
}
```

替换方式：

```text
写 current.json.tmp
fsync/close
os.replace
```

------

# 33. `verify`

```powershell
juce-doc verify `
  --juce-root .\JUCE `
  --reference .\.agent-docs\juce
```

验证：

- 当前 JUCE SHA 与 lock 一致
- dirty 状态符合要求
- Doxygen 版本符合 lock
- manifest hashes
- 文件集合
- 索引可读取
- SQLite metadata
- 关键查询
- source 和 example 路径
- current.json 指向有效 release

任何不一致返回退出码 14。

------

# 34. Smoke Test

`smoke_test.py` 对真实 JUCE checkout 验证至少以下符号：

```text
juce::AudioProcessor
juce::AudioProcessorValueTreeState
juce::Component
juce::SmoothedValue
juce::dsp::ProcessorChain
```

每个符号至少检查：

- symbol 可查询
- Markdown 文件存在
- signature 或 declaration 存在
- source path 存在
- module 正确或非空
- 内部链接有效

至少检查一类：

- inheritance
- overloaded method
- template class
- enum
- documentation code block
- official example

Smoke test 必须使用真实 JUCE，不得只使用 fixture。

------

# 35. 搜索质量测试

固定查询集：

| Query                          | 预期目标                             |
| ------------------------------ | ------------------------------------ |
| `AudioProcessorValueTreeState` | `juce::AudioProcessorValueTreeState` |
| `APVTS`                        | `juce::AudioProcessorValueTreeState` |
| `save plugin parameter state`  | APVTS 和状态相关成员                 |
| `smooth parameter changes`     | `juce::SmoothedValue`                |
| `DSP processor chain`          | `juce::dsp::ProcessorChain`          |
| `plugin editor resize`         | `AudioProcessorEditor`、`Component`  |
| `MIDI message timestamp`       | 相关 MIDI API                        |

验收：

- 精确 symbol：第 1
- 人工别名：目标 Top 3
- 概念查询：目标 Top 5
- internal/undocumented 不无理由排在公开 API 前

查询预期保存在：

```text
tests/fixtures/search/quality.yml
```

Agent 可以增加查询，但不得降低已有排名要求来通过测试。

------

# 36. 确定性测试

`determinism.py`：

同一：

- JUCE commit
- Doxygen version
- generator version
- config
- aliases

执行两次生成。

比较：

- 文件集合
- Markdown bytes
- JSON bytes
- JSONL bytes
- TSV bytes
- manifest
- SQLite 逻辑导出

排除：

```text
reports/generation.json
reports/doxygen-warnings.log
临时路径日志
```

SQLite 文件不要求逐字节相同，但必须导出相同逻辑行。

------

# 37. `test` 和 `all`

## 37.1 `juce-doc test`

运行：

```text
pytest
ruff check .
mypy src
```

可选：

```text
--unit-only
--integration
```

## 37.2 `juce-doc all`

这是 Goal 的唯一最终成功入口。

顺序固定：

```text
1. doctor
2. pytest unit
3. pytest integration
4. ruff
5. mypy
6. generate real JUCE reference
7. validate output
8. smoke
9. search quality
10. determinism
11. verify
12. repository cleanliness
13. progress completion check
14. blocker absence check
```

任一步失败立即返回对应非零退出码。

成功后输出机器可读摘要：

```json
{
  "passed": true,
  "juce_commit": "...",
  "tests": {
    "pytest": "...",
    "ruff": "passed",
    "mypy": "passed",
    "smoke": "passed",
    "search_quality": "passed",
    "determinism": "passed",
    "verify": "passed"
  }
}
```

不得通过跳过检查让 `all` 返回 0。

------

# 38. Bootstrap 脚本

## 38.1 `scripts/bootstrap.ps1`

职责：

- 检查 Python
- 创建 `.venv`
- 安装 editable dev dependencies
- 检查 Git
- 检查 Doxygen
- 初始化 progress
- 运行 `doctor`

不得：

- 自动以管理员权限安装系统软件
- 修改系统安全策略
- 修改 JUCE checkout
- 下载未知二进制

## 38.2 `scripts/bootstrap.sh`

实现等价行为。

## 38.3 `goal-check`

只运行最终验收：

```powershell
python -m juce_reference all ...
```

并额外检查：

```text
git status --porcelain
.agent/blocker.json 不存在
progress.json completed=true
```

------

# 39. 自动进度状态

`progress.py` 管理：

```text
.agent/progress.json
```

Schema：

```json
{
  "schema_version": 1,
  "goal": "Complete JUCE Agent Reference V1",
  "current_phase": 1,
  "completed_phases": [],
  "last_verified_commit": null,
  "last_successful_command": null,
  "current_failure": null,
  "next_action": "Initialize repository",
  "completed": false
}
```

## 39.1 更新时机

必须在以下时机更新：

- 开始 Phase
- Phase 验证成功
- 创建 Phase commit
- 命令失败
- 修复完成
- 进入下一 Phase
- 最终验收通过

## 39.2 原子写入

写：

```text
progress.json.tmp
```

再：

```python
os.replace(...)
```

## 39.3 恢复

Goal 被中断后：

1. 读取 progress
2. 检查 last commit
3. 检查 Git 状态
4. 验证最近完成 Phase
5. 从 `next_action` 继续

若 progress 与 Git 历史不一致，以实际 Git 和测试结果为准，并修复 progress。

------

# 40. Blocker 文件

只有不可恢复外部阻断才写：

```text
.agent/blocker.json
```

Schema：

```json
{
  "schema_version": 1,
  "phase": 2,
  "command": "doxygen --version",
  "error": "Executable not found",
  "attempts": [
    "Checked PATH",
    "Checked common installation locations"
  ],
  "last_verified_commit": "...",
  "completed_phases": [1],
  "required_external_action": "Install the locked Doxygen version and rerun bootstrap"
}
```

普通代码错误、测试失败、XML 新节点不得写 blocker。

问题恢复后必须删除 blocker 并继续。

------

# 41. Git 提交规则

每个 Phase 至少一个本地 commit。

建议提交：

```text
chore: initialize JUCE reference generator
feat: validate JUCE checkout and generate Doxygen XML
feat: parse Doxygen XML into canonical model
feat: render linked JUCE Markdown reference
feat: build deterministic symbol and search indexes
feat: index JUCE examples and source locations
feat: validate and atomically publish references
feat: add unattended goal execution and final verification
```

每个 commit：

- 范围单一
- 测试通过
- 不含临时构建
- 不含 JUCE checkout
- 不含大体积生成 XML
- 不含失败日志
- 更新 progress

Agent 不得：

- 自动 push
- force push
- rebase 已共享远程历史
- 修改远程分支
- 删除用户已有提交
- 提交密钥或绝对敏感路径

最终：

```text
git status --porcelain
```

必须为空。

------

# 42. Phase 实施顺序

## Phase 1：仓库和执行框架

实现：

- pyproject
- CLI 框架
- errors
- config
- command helper
- BuildContext
- progress
- bootstrap
- 基础测试

验收：

```text
pytest 基础测试通过
ruff 通过
mypy 通过
doctor 可运行
```

提交后更新 Phase 1 完成。

## Phase 2：JUCE 输入与 Doxygen

实现：

- source
- doctor 完整检查
- doxygen runner
- XML validator
- toolchain lock

验收：

- 固定 JUCE checkout 可生成 XML
- Doxygen 版本不一致失败
- dirty 默认失败
- 官方 Doxyfile 未修改
- Schema 校验通过

## Phase 3：IR 和 Parser

实现：

- documentation nodes
- model
- index parser
- compound parser
- member parser
- 代码块
- source location
- disposition

验收：

- fixture 完整
- 新未知语义节点失败
- 文档代码块保留
- 普通源码不进入 IR 文档

## Phase 4：路径和 Markdown

实现：

- PathMap
- 冲突处理
- member anchor
- Renderer
- repository docs
- golden tests
- link validator 基础

验收：

- 代表类型可生成
- 重载锚点不同
- 内部链接有效
- Windows casefold 无冲突

## Phase 5：索引和查询

实现：

- aliases
- symbols TSV/JSONL
- relationships
- FTS5
- symbol
- show
- search
- related
- rebuild-index

验收：

- 精确查询第 1
- SQLite 可重建
- 文本索引可用
- 搜索质量基础通过

## Phase 6：示例和源码

实现：

- example scanner
- examples JSONL
- examples Markdown
- API 反向链接
- source index
- examples CLI
- source CLI

验收：

- 官方示例可查询
- 关联有置信度
- 声明准确
- 不确定定义不猜测

## Phase 7：验证和发布

实现：

- output validator
- manifest
- docs lock
- publisher
- verify
- atomic current

验收：

- 全部内部链接通过
- release 可原子发布
- dirty 不发布
- 同 commit 不同内容失败

## Phase 8：无人值守验收

实现：

- smoke
- search quality
- determinism
- test
- all
- goal-check
- final progress logic
- repository cleanliness

验收：

```text
juce-doc all 返回 0
progress.completed = true
无 blocker
Git 工作区干净
```

------

# 43. 测试体系

## 43.1 单元测试

覆盖：

- Git 命令解析
- Doxygen version
- XML 节点
- DocNode
- signature
- path collision
- anchor
- relative link
- aliases
- example detection
- search ranking
- atomic file writes

## 43.2 Golden Tests

最小 Doxygen fixture 覆盖：

- class
- struct
- inheritance
- overload
- template
- constructor
- enum
- enum value
- typedef
- using
- macro
- deprecated
- note
- warning
- parameter
- return
- throws
- code block
- internal reference
- external URL
- protected member
- undocumented public member

## 43.3 Integration Tests

真实运行 Doxygen：

```text
fixture C++ source
→ Doxygen XML
→ IR
→ Markdown
→ Index
→ Validation
```

验证：

- `XML_PROGRAMLISTING = NO`
- 代码片段保留
- 函数体未复制
- 签名完整

## 43.4 Real JUCE Test

不把完整 JUCE 生成物提交为 fixture。

CI 或本地 Goal 使用指定真实 checkout。

------

# 44. 禁止伪完成

Agent 不得：

- 留下核心 `pass`
- 留下核心 `NotImplementedError`
- 使用假数据通过 smoke test
- 使用空文档通过 output validator
- 将失败测试标记 skip
- 删除不容易通过的测试
- 降低 Top-K 要求
- 把真实 smoke test替换成 fixture
- 将错误改成 warning 规避
- 对 XML 使用无条件 `.itertext()`
- 忽略 unresolved internal references
- 返回猜测 source location
- 把未来功能写入 README 后声明完成
- 只报告“项目基本完成”

测试中的 TODO 必须是明确非 V1 范围，且不得位于核心执行路径。

------

# 45. 普通失败处理协议

当命令失败：

```text
1. 保存完整命令和输出
2. 更新 progress.current_failure
3. 缩小失败范围
4. 建立回归测试或 fixture
5. 修复实现
6. 运行局部测试
7. 运行当前 Phase 测试
8. 清除 current_failure
9. 更新 next_action
10. 继续执行
```

不得因连续失败询问用户，除非符合外部 blocker 定义。

------

# 46. 最终统一验收

最终执行：

```powershell
juce-doc all `
  --juce-root <JUCE> `
  --output <reference-output>
```

然后：

```powershell
scripts/goal-check.ps1
```

必须确认：

- 返回码 0
- 所有 Phase 完成
- `progress.completed=true`
- blocker 不存在
- Git clean
- commit 列表完整
- README 使用说明完整
- AGENTS.md 查询协议完整
- plan 和 implementation 未被擅自降级

只有这一步通过，Agent 才能输出最终完成报告。

------

# 47. 最终报告格式

```markdown
# Final Implementation Report

## Result

V1 completed / blocked

## JUCE and toolchain

- JUCE commit:
- JUCE dirty:
- Python:
- Doxygen:
- Generator:

## Completed phases

- Phase 1:
- Phase 2:
- ...

## Commits

- `<sha>` description

## Verification

- doctor:
- pytest:
- integration:
- ruff:
- mypy:
- generate:
- output validation:
- smoke:
- search quality:
- determinism:
- verify:
- goal-check:

## Output

- Reference release:
- Manifest:
- Symbol count:
- Document count:
- Example count:

## Known non-blocking limitations

仅列出 plan.md 明确不属于 V1 的内容。

## Repository state

- Git clean:
- Blocker file:
- Progress completed:
```

不能把未满足的 V1 项目写入“known limitation”后宣布成功。

------

# 48. Definition of Done 映射

执行 Agent 应建立 `plan.md` Definition of Done 到测试或命令的映射。

建议生成：

```text
tests/definition-of-done.yml
```

示例：

```yaml
- id: input.doxygen_locked
  plan_requirement: Doxygen 使用锁定的精确版本
  verification:
    - tests/test_doctor.py::test_rejects_wrong_doxygen_version
    - juce-doc doctor

- id: markdown.code_blocks
  plan_requirement: 文档代码块被完整保留
  verification:
    - tests/integration/test_documentation_code.py

- id: search.exact_first
  plan_requirement: 精确 symbol 查询稳定排第 1
  verification:
    - tests/test_search.py::test_exact_symbol_ranked_first
    - juce-doc search-quality

- id: publish.atomic
  plan_requirement: 构建失败不会覆盖旧版本
  verification:
    - tests/test_publisher.py::test_failed_publish_preserves_current
```

最终 `all` 应检查每个 DoD 项都存在机器验证映射。

------

# 49. Agent 启动顺序

Goal Agent 启动后必须：

1. 阅读 `AGENTS.md`
2. 阅读 `plan.md`
3. 阅读 `implementation.md`
4. 检查 Git 历史
5. 读取 `.agent/progress.json`
6. 运行 bootstrap 或 doctor
7. 确定当前 Phase
8. 持续实施
9. 每 Phase 测试和 commit
10. 最终运行 `juce-doc all`
11. 运行 goal-check
12. 输出最终报告

不得再次只生成实施计划而不写代码。

------

# 50. 最终实施结论

项目必须形成以下完整闭环：

```text
指定 JUCE checkout
        ↓
环境和版本校验
        ↓
官方 Doxygen XML
        ↓
XML Schema 校验
        ↓
Canonical IR
        ↓
Markdown API 文档
        ↓
符号、关系、示例和源码索引
        ↓
FTS5 查询缓存
        ↓
完整性验证
        ↓
真实 JUCE smoke test
        ↓
搜索质量测试
        ↓
确定性测试
        ↓
原子发布
        ↓
版本 verify
        ↓
统一机器验收
```

自动化执行闭环：

```text
读取三份规范
        ↓
按 Phase 实施
        ↓
失败自动建立回归测试
        ↓
修复并继续
        ↓
本地 Git 提交
        ↓
持久化进度
        ↓
中断后恢复
        ↓
全部验收通过
        ↓
Goal 完成
```

只有 `juce-doc all` 和 `goal-check` 均成功、Git 工作区干净、`.agent/progress.json` 标记完成且不存在 `.agent/blocker.json` 时，Agent 才允许声明 JUCE Agent Reference V1 已完整实现。
# GeoTask Core v0.2.0 Artifact Contracts Release

- **Release date:** 2026-07-30
- **Git tag:** `v0.2.0`
- **Package version:** `0.2.0`
- **GeoTask Document Schema:** `1.0`
- **Artifact Registry:** `1.0`
- **Artifact Validation Report:** `1.0`
- **Schema Bundle:** `1.0`

## 中文发布说明

GeoTask Core v0.2.0将公共Core从“可安装、可执行”推进到“制品可发现、Schema可离线获取、完整性可验证、验证结果可再次验证”。这是一个向后兼容的0.x次版本升级：原有任务文档、确定性执行、`geotask validate`、`geotask result validate`和`geotask control validate`继续可用，同时新增面向Agent、IDE、CI和第三方工具的统一公共契约。

### 主要新增

#### 1. 公共Artifact Registry

```bash
geotask inspect schemas --format json
geotask inspect schemas geotask.execution-result --format json
geotask inspect schemas --verify --format json
```

Registry稳定注册四类公共制品：

- `geotask.document`
- `geotask.execution-result`
- `geotask.control-evaluation`
- `geotask.artifact-validation-report`

每个描述符公开稳定Artifact ID、Schema ID与版本、仓库路径、生成命令、验证命令和非执行边界。

#### 2. 离线Schema Bundle与完整性验证

wheel和sdist包含五份公共JSON Schema及自动生成的`schema-bundle-manifest-v1.0.json`。Manifest记录每份Schema的文件名、字节数和SHA-256摘要。

```bash
geotask schema export geotask.execution-result --compact
geotask schema export geotask.artifact-validation-report \
  --output artifact-validation.schema.json
geotask schema verify --format json
```

Schema加载、导出和Artifact验证都会检查文件名、字节数、SHA-256、JSON对象形态和发布的`$id`。这些摘要用于证明发行包内部一致性，不等同于数字签名或外部发布者认证。源码检出环境可从仓库根目录的权威Schema计算等价Manifest；安装包若缺少已发布Manifest则直接失败关闭，不会现场重建信任元数据。

#### 3. 统一Artifact验证入口

```bash
geotask artifact validate \
  geotask.document task.yaml

geotask artifact validate \
  geotask.execution-result execution-result.json \
  --format json

geotask artifact validate \
  geotask.control-evaluation control-evaluation.json \
  --format json
```

统一命令按Artifact ID分发到现有严格语义验证器，输出`artifact_validation/1.0`报告。验证只读取输入，不执行算子、不重跑任务、不重新计算控制决策、不执行`next_action`、不释放输出。

#### 4. 验证报告可作为公共制品再次验证

```bash
geotask artifact validate \
  geotask.execution-result execution-result.json \
  --format json > artifact-validation.json

geotask artifact validate \
  geotask.artifact-validation-report artifact-validation.json \
  --format json
```

严格报告加载器会校验目标Artifact是否注册，并核对`artifact_kind`、`schema_id`和`schema_version`是否与Registry一致，同时检查`valid`、`schema_verified`和错误诊断之间的交叉约束。验证报告自身时不会重新验证原始目标文件。一个如实记录原始目标无效的报告，仍可以是结构和语义均有效的验证报告制品。

#### 5. 公共Python API

```python
from geotask_core import (
    list_artifact_descriptors,
    artifact_registry_payload,
    load_artifact_schema,
    verify_schema_bundle,
    validate_artifact_file,
    validate_artifact_payload,
    load_artifact_validation_report,
)
```

同一组名称也从`geotask_core.v1`导出。

#### 6. 发布身份预检

```bash
python .release/verify_release_preflight.py \
  --expected-version 0.2.0 \
  --expected-tag v0.2.0 \
  --artifacts dist \
  --format json
```

预检统一核对版本源、`CITATION.cff`、CHANGELOG、Git标签文本、Release Notes、双语Quickstart、README导航，以及wheel/sdist文件名和包内版本元数据。PyPI手工工作流从默认分支启动，要求显式输入预期版本，随后明确检出对应的`v<版本>`标签并核对HEAD；非默认分支、缺失或错误标签、输入值与源码版本不一致都会在构建上传前失败。

### 安装与核验

```bash
python -m pip install --no-cache-dir geotask-core==0.2.0
python -c "from importlib.metadata import version; import geotask_core; print(version('geotask-core')); print(geotask_core.__version__)"
geotask --version
geotask schema verify
geotask inspect schemas --verify --format json
```

发行元数据、`geotask_core.__version__`和CLI均应报告`0.2.0`；Schema Bundle应报告5份Schema有效；Registry应报告4类公共制品。

### 验证结果

- 完整源仓：`1070 passed, 1 skipped`；
- 发布治理聚焦回归：`61 passed`；
- wheel与sdist构建通过；
- 从sdist重建wheel并通过同一五-Schema制品门禁；
- 隔离环境安装后，Registry发现、Schema导出、Schema完整性检查、三类基础制品验证和验证报告自验证全部通过；
- wheel与sdist均通过Twine检查；
- 公共发布流水线导出253个文件，边界检查、导出验证、敏感扫描、哈希生成和哈希校验全部通过；
- UTF-8文本在公开哈希生成和校验时统一规范化为LF，Windows CRLF导出与Linux/GitHub检出使用同一稳定摘要。

## English release notes

GeoTask Core v0.2.0 advances the public Core from installable deterministic execution to discoverable artifacts, offline schemas, integrity verification, and validation reports that can themselves be validated. This is a backward-compatible 0.x minor release: existing task documents, deterministic execution, `geotask validate`, `geotask result validate`, and `geotask control validate` remain available, while Agent, IDE, CI, and third-party clients gain one stable public contract surface.

### Highlights

#### 1. Public Artifact Registry

```bash
geotask inspect schemas --format json
geotask inspect schemas geotask.execution-result --format json
geotask inspect schemas --verify --format json
```

The Registry exposes four stable public artifacts:

- `geotask.document`
- `geotask.execution-result`
- `geotask.control-evaluation`
- `geotask.artifact-validation-report`

Each descriptor publishes its stable Artifact ID, Schema ID and version, repository paths, generation and validation guidance, and explicit non-execution boundary.

#### 2. Offline Schema Bundle and integrity verification

Wheels and source distributions contain five public JSON Schemas plus an automatically generated `schema-bundle-manifest-v1.0.json`. The manifest records each filename, byte size, and SHA-256 digest.

```bash
geotask schema export geotask.execution-result --compact
geotask schema export geotask.artifact-validation-report \
  --output artifact-validation.schema.json
geotask schema verify --format json
```

Schema loading, export, and Artifact validation verify filenames, byte sizes, SHA-256 digests, JSON object shape, and the published `$id`. These digests prove internal distribution consistency; they are not digital signatures or external publisher attestations. A source checkout may compute an equivalent Manifest from the repository's authoritative Schemas; an installed package fails closed when its published Manifest is missing and never reconstructs trust metadata at runtime.

#### 3. Unified Artifact validation

```bash
geotask artifact validate geotask.document task.yaml
geotask artifact validate \
  geotask.execution-result execution-result.json --format json
geotask artifact validate \
  geotask.control-evaluation control-evaluation.json --format json
```

The command dispatches by stable Artifact ID to the existing strict semantic validators and emits an `artifact_validation/1.0` report. Validation is read-only: it does not execute operators, rerun tasks, reevaluate control decisions, execute `next_action`, or release outputs.

#### 4. Validation reports are registered and self-validating

```bash
geotask artifact validate \
  geotask.execution-result execution-result.json \
  --format json > artifact-validation.json

geotask artifact validate \
  geotask.artifact-validation-report artifact-validation.json \
  --format json
```

The strict report loader verifies that the target Artifact is registered, that `artifact_kind`, `schema_id`, and `schema_version` match Registry metadata, and that `valid`, `schema_verified`, and error diagnostics are mutually consistent. It does not repeat validation of the original target file. A report that truthfully records an invalid target may still be a valid report artifact.

#### 5. Public Python API

```python
from geotask_core import (
    list_artifact_descriptors,
    artifact_registry_payload,
    load_artifact_schema,
    verify_schema_bundle,
    validate_artifact_file,
    validate_artifact_payload,
    load_artifact_validation_report,
)
```

The same names are exported from `geotask_core.v1`.

#### 6. Release identity preflight

```bash
python .release/verify_release_preflight.py \
  --expected-version 0.2.0 \
  --expected-tag v0.2.0 \
  --artifacts dist \
  --format json
```

The preflight checks the version source, `CITATION.cff`, CHANGELOG, Git tag text, Release Notes, bilingual Quickstarts, README navigation, wheel/sdist filenames, and embedded package metadata. The manual PyPI workflow is dispatched from the default branch, requires an explicit expected version, then checks out the matching `v<version>` tag and verifies HEAD; a non-default branch, missing or mismatched tag, or source-version mismatch fails before build and upload.

### Install and verify

```bash
python -m pip install --no-cache-dir geotask-core==0.2.0
python -c "from importlib.metadata import version; import geotask_core; print(version('geotask-core')); print(geotask_core.__version__)"
geotask --version
geotask schema verify
geotask inspect schemas --verify --format json
```

Distribution metadata, `geotask_core.__version__`, and the CLI should report `0.2.0`. Schema verification should report five valid schemas, and Registry discovery should report four public artifacts.

### Verification

- Full source repository: `1070 passed, 1 skipped`;
- Focused release-governance regression suite: `61 passed`;
- wheel and sdist builds passed;
- a wheel rebuilt from the sdist passed the same five-Schema distribution gate;
- isolated installed CLI/API smoke tests passed for Registry discovery, Schema export and verification, base Artifact validation, and validation-report self-validation;
- wheel and sdist passed Twine checks;
- the public release pipeline exported 253 files and passed boundary checks, export verification, sensitive scanning, hash generation, and hash verification;
- public hashing normalizes UTF-8 text to LF, so Windows CRLF exports and Linux/GitHub checkouts share one stable digest set.

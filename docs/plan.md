目前仓库基本只有原始数据、数据说明、作业 PDF 和报告模板，还没有代码结构，因此现在正适合先统一框架，再让两个人分别开发。

第 3 题的数据是固定快照 `CISA_KEV_2026-07-29.json`，共 1,656 条记录。需要特别处理多值 `cwes`、厂商和产品字段首尾空格，同时保留原始字段；171 条空 CWE 记录不能删除，也不能随便填充占位值。

## 一、整体技术方案

建议使用：

* 数据处理：`pandas`
* 统计与计算：`numpy`
* 交互式图表：`plotly`
* HTML 报告模板：`Jinja2`
* 测试：`pytest`
* 配置：YAML 或 Python dataclass
* 最终报告：一个可离线打开的自包含 HTML 文件

不建议使用 Dash、Streamlit、Flask 等服务端框架，因为你们不做 GUI，而是提交交互式 HTML 报告。Plotly 图表嵌入 Jinja2 页面就足够了。

整体数据流为：

```text
原始 JSON
   ↓
读取与完整性验证
   ↓
统一清洗后的 prepared DataFrame
   ├── 时间 / 截止期限 / 勒索软件分析
   ├── 厂商 / 产品 / 集中度分析
   └── CWE 展开 / 组合查询
             ↓
       表格 + 指标 + Plotly Figure
             ↓
        Jinja2 HTML 报告
             ↓
report/output/kev_report.html
```

---

# 二、统一目录框架

建议把仓库调整为：

```text
CISA/
├── data/
│   ├── CISA_KEV_2026-07-29.json
│   └── 数据说明.txt
│
├── docs/
│   ├── 大作业_en.pdf
│   └── 大作业模板.docx
│
├── src/
│   └── kev_analysis/
│       ├── __init__.py
│       ├── config.py
│       ├── constants.py
│       │
│       ├── data/
│       │   ├── __init__.py
│       │   ├── loader.py
│       │   ├── validator.py
│       │   └── prepare.py
│       │
│       ├── analysis/
│       │   ├── __init__.py
│       │   ├── temporal.py
│       │   ├── ransomware.py
│       │   ├── vendor.py
│       │   ├── cwe.py
│       │   └── queries.py
│       │
│       ├── visualization/
│       │   ├── __init__.py
│       │   ├── temporal_charts.py
│       │   ├── vendor_charts.py
│       │   └── cwe_charts.py
│       │
│       ├── reporting/
│       │   ├── __init__.py
│       │   ├── report_builder.py
│       │   └── serializers.py
│       │
│       └── utils/
│           ├── paths.py
│           ├── logging.py
│           └── export.py
│
├── scripts/
│   ├── run_pipeline.py
│   └── verify_outputs.py
│
├── report/
│   ├── templates/
│   │   ├── report.html.j2
│   │   └── sections/
│   │       ├── 01_overview.html.j2
│   │       ├── 02_data_quality.html.j2
│   │       ├── 03_temporal.html.j2
│   │       ├── 04_vendor.html.j2
│   │       ├── 05_cwe.html.j2
│   │       ├── 06_queries.html.j2
│   │       └── 07_limitations.html.j2
│   │
│   ├── assets/
│   │   └── report.css
│   │
│   └── output/
│       └── kev_report.html
│
├── outputs/
│   ├── prepared/
│   ├── tables/
│   ├── figures/
│   ├── queries/
│   ├── metrics/
│   └── logs/
│
├── tests/
│   ├── test_loader.py
│   ├── test_validator.py
│   ├── test_prepare.py
│   ├── test_temporal.py
│   ├── test_vendor.py
│   ├── test_cwe.py
│   └── test_queries.py
│
├── config/
│   └── analysis.yaml
│
├── pyproject.toml
├── requirements.txt
├── README.md
└── .gitignore
```

这样满足：

* 原始数据和代码分开；
* 报告模板、样式、最终 HTML 和代码分开；
* 四个分析模块彼此分开；
* 两个人基本不会同时修改同一个文件；
* 中间表、图、查询结果统一输出到 `outputs/`。

---

# 三、公共数据层必须先统一

两个人并行开发前，必须先确定统一的 `prepared_df`。

## 1. 原始字段

保留全部 11 个原始字段：

```python
ORIGINAL_COLUMNS = [
    "cveID",
    "vendorProject",
    "product",
    "vulnerabilityName",
    "dateAdded",
    "shortDescription",
    "requiredAction",
    "dueDate",
    "knownRansomwareCampaignUse",
    "notes",
    "cwes",
]
```

## 2. 新增清洗字段

统一增加：

```text
vendor_clean
product_clean
date_added
due_date
deadline_days
year_added
month_added
```

建议含义：

| 字段              | 类型            | 说明                          |
| --------------- | ------------- | --------------------------- |
| `vendor_clean`  | str           | `vendorProject.str.strip()` |
| `product_clean` | str           | `product.str.strip()`       |
| `date_added`    | datetime      | 解析后的 `dateAdded`            |
| `due_date`      | datetime      | 解析后的 `dueDate`              |
| `deadline_days` | int           | `due_date - date_added`     |
| `year_added`    | int           | 加入 KEV 的年份                  |
| `month_added`   | period/string | 例如 `2025-07`                |

原始的 `vendorProject`、`product`、`dateAdded` 和 `dueDate` 不删除、不覆盖。数据说明明确要求只通过 `str.strip()` 建立确定性清理列，不进行模糊厂商合并。

## 3. 公共接口

```python
def load_catalog(path: Path) -> tuple[dict, pd.DataFrame]:
    """读取顶层元数据和 vulnerabilities DataFrame."""


def validate_catalog(
    metadata: dict,
    df: pd.DataFrame,
) -> ValidationResult:
    """完成结构、字段、格式、唯一性和逻辑关系验证."""


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """返回新 DataFrame，不修改输入对象."""
```

`ValidationResult` 建议使用 dataclass：

```python
@dataclass
class ValidationResult:
    passed: bool
    checks: dict[str, bool]
    statistics: dict[str, Any]
    errors: list[str]
    warnings: list[str]
```

验证结果不要只通过 `assert` 打印在终端，而应导出：

```text
outputs/metrics/validation_report.json
outputs/tables/field_quality.csv
outputs/logs/validation.log
```

---

# 四、四个必做模块的代码组织

## 模块一：读取、验证和预处理

文件：

```text
src/kev_analysis/data/loader.py
src/kev_analysis/data/validator.py
src/kev_analysis/data/prepare.py
```

主要完成：

* JSON 顶层字段检查；
* `count == len(vulnerabilities)`；
* 11 个字段完整性；
* CVE 非空、格式正确且唯一；
* 日期可解析；
* `dueDate >= dateAdded`；
* 勒索软件字段只能为 `Known` 或 `Unknown`；
* `cwes` 必须是列表；
* CWE 元素满足 `CWE-[数字]`；
* 空值、空字符串、字段类型统计；
* SHA-256 校验；
* 创建清洗列；
* 导出准备好的数据。

建议输出：

```text
outputs/prepared/kev_prepared.csv
outputs/metrics/catalog_metadata.json
outputs/metrics/validation_report.json
outputs/tables/field_quality.csv
```

CSV 中 `cwes` 可以序列化成：

```text
CWE-79|CWE-89
```

但程序内部始终保持 Python 列表。

---

## 模块二：时间、截止期限和勒索软件分析

文件：

```text
src/kev_analysis/analysis/temporal.py
src/kev_analysis/analysis/ransomware.py
src/kev_analysis/visualization/temporal_charts.py
```

建议函数：

```python
def build_monthly_series(df: pd.DataFrame) -> pd.DataFrame:
    """生成 2021-11 至 2026-07 的连续月份序列."""


def build_annual_summary(df: pd.DataFrame) -> pd.DataFrame:
    """年度数量、占比及完整年份标记."""


def analyze_deadlines(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """截止期限描述统计、频数和年度比较."""


def analyze_ransomware(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Known/Unknown 总体与年度统计."""
```

建议输出：

```text
outputs/tables/monthly_additions.csv
outputs/tables/annual_additions.csv
outputs/tables/deadline_summary.csv
outputs/tables/deadline_frequency.csv
outputs/tables/deadline_by_year.csv
outputs/tables/ransomware_summary.csv
outputs/tables/ransomware_by_year.csv
```

图表建议：

1. 每月新增 KEV 折线图；
2. 每年新增数量柱状图；
3. `deadline_days` 分布直方图；
4. 各年度期限箱线图；
5. Known/Unknown 总体占比图；
6. 各年度 Known/Unknown 堆叠图。

注意：

* 2021 和 2026 是不完整年份，报告里必须明确标记；
* `dateAdded` 是加入 KEV 的时间，不是漏洞披露时间；
* `dueDate-dateAdded` 只能解释为目录要求中的处置期限，不能解释成实际修复耗时。

---

## 模块三：厂商、产品和集中度

文件：

```text
src/kev_analysis/analysis/vendor.py
src/kev_analysis/visualization/vendor_charts.py
```

建议函数：

```python
def build_vendor_summary(df: pd.DataFrame) -> pd.DataFrame:
    ...


def build_vendor_product_summary(df: pd.DataFrame) -> pd.DataFrame:
    ...


def calculate_concentration(
    vendor_summary: pd.DataFrame,
) -> dict[str, float]:
    ...
```

### 厂商汇总表

建议字段：

```text
rank
vendor_clean
count
share
cumulative_share
known_count
unknown_count
known_share
unknown_share
```

其中：

```python
share = count / total_records
cumulative_share = share.cumsum()
known_share = known_count / count
unknown_share = unknown_count / count
```

CSV 中占比必须保存为 `[0,1]` 小数，只有 HTML 展示时才格式化成百分比。

### 厂商—产品汇总表

建议字段：

```text
rank
vendor_clean
product_clean
count
share
cumulative_share
```

排序统一规定为：

```text
count 降序
vendor_clean 升序
product_clean 升序
```

这样相同数量时输出结果稳定。

### 集中度指标

```python
CR5 = vendor_summary.head(5)["share"].sum()
CR10 = vendor_summary.head(10)["share"].sum()
HHI = (vendor_summary["share"] ** 2).sum()
```

必须使用小数占比计算 HHI，不能直接对百分数平方。

建议输出：

```text
outputs/tables/vendor_summary.csv
outputs/tables/vendor_product_summary.csv
outputs/tables/top30_vendor_products.csv
outputs/metrics/vendor_concentration.json
```

建议图表：

1. Top 20 厂商横向柱状图；
2. Top 30 厂商—产品组合图；
3. 厂商累计占比 Pareto 图；
4. 厂商 Known/Unknown 对比图；
5. CR5、CR10、HHI 指标卡片。

报告只能表述为：

> 这些厂商标签在 KEV 目录记录中的集中程度。

不能写成：

> 某厂商更不安全、产品质量更差或更容易被攻击。

因为 KEV 不包含市场占有率、资产数量、攻击次数等信息。

---

## 模块四：CWE 展开和组合查询

文件：

```text
src/kev_analysis/analysis/cwe.py
src/kev_analysis/analysis/queries.py
src/kev_analysis/visualization/cwe_charts.py
```

### CWE 展开

```python
def explode_cwes(df: pd.DataFrame) -> pd.DataFrame:
    ...
```

处理原则：

* 只在 CWE 专项表中展开；
* 原始 `prepared_df` 不展开；
* 空 CWE 记录不进入 exploded 表；
* 不给空 CWE 填 `Unknown`；
* 一条 CVE 可以对应多个 CWE，因此展开后的行数可以大于 1,656。

建议展开表字段：

```text
cveID
date_added
year_added
vendor_clean
product_clean
knownRansomwareCampaignUse
cwe
```

CWE 汇总建议字段：

```text
rank
cwe
cve_count
record_share
known_count
unknown_count
known_share
unknown_share
```

`cve_count` 应使用：

```python
groupby("cwe")["cveID"].nunique()
```

避免因为错误重复展开造成重复计数。

建议输出：

```text
outputs/prepared/cwe_exploded.csv
outputs/tables/cwe_summary.csv
outputs/tables/cwe_by_year.csv
outputs/tables/cwe_ransomware_comparison.csv
```

### 组合查询函数

函数签名固定为：

```python
def filter_kev(
    df: pd.DataFrame,
    start_date=None,
    end_date=None,
    vendor=None,
    ransomware=None,
    cwe=None,
) -> tuple[pd.DataFrame, dict]:
    ...
```

必须遵守：

* 日期为闭区间；
* vendor 对 `vendor_clean` 做大小写不敏感的子串匹配；
* ransomware 只能为 `Known`、`Unknown` 或 `None`；
* 非法 ransomware 值抛出 `ValueError`；
* CWE 转成大写后做完整值匹配；
* 所有条件使用 AND；
* 不修改传入 DataFrame；
* 最终按 `dateAdded` 降序、`cveID` 升序排列；
* 返回实际结果和 summary。

summary 建议格式：

```python
{
    "filters": {
        "start_date": "...",
        "end_date": "...",
        "vendor": "...",
        "ransomware": "...",
        "cwe": "...",
    },
    "result_count": 23,
    "unique_vendors": 5,
    "unique_products": 12,
    "date_min": "...",
    "date_max": "...",
}
```

至少预设三个查询案例，例如：

```text
案例 1：指定日期范围 + Known
案例 2：指定厂商 + CWE
案例 3：日期范围 + 厂商 + ransomware + CWE
```

每个查询导出：

```text
outputs/queries/query_01_results.csv
outputs/queries/query_01_summary.json
outputs/queries/query_02_results.csv
outputs/queries/query_02_summary.json
outputs/queries/query_03_results.csv
outputs/queries/query_03_summary.json
outputs/logs/query_log.json
```

---

# 五、统一的模块返回格式

为了避免报告层依赖每个人的内部代码，所有分析模块统一返回：

```python
@dataclass
class AnalysisArtifacts:
    tables: dict[str, pd.DataFrame]
    metrics: dict[str, Any]
    figures: dict[str, go.Figure]
    notes: list[str]
```

例如：

```python
temporal_result = AnalysisArtifacts(
    tables={
        "monthly": monthly_df,
        "annual": annual_df,
        "deadline": deadline_df,
    },
    metrics={
        "total_records": 1656,
    },
    figures={
        "monthly_trend": monthly_fig,
        "deadline_distribution": deadline_fig,
    },
    notes=[
        "2021 and 2026 are partial years."
    ],
)
```

报告层只处理 `AnalysisArtifacts`，不重新计算统计结果。

这点非常重要：**HTML 报告只能展示分析模块已经计算出的结果，不能在 Jinja2 模板中重新 groupby、计算占比或 HHI。**

---

# 六、HTML 报告框架

最终文件：

```text
report/output/kev_report.html
```

页面建议包含：

```text
1. 标题与数据集信息
2. 执行摘要
3. 数据质量与验证结果
4. 时间趋势分析
5. 截止期限分析
6. 勒索软件标记分析
7. 厂商及产品分布
8. 厂商标签集中度
9. CWE 结构分析
10. 组合查询案例
11. 数据局限性与结论边界
12. 方法和可复现说明
```

顶层模板：

```html
{% include "sections/01_overview.html.j2" %}
{% include "sections/02_data_quality.html.j2" %}
{% include "sections/03_temporal.html.j2" %}
{% include "sections/04_vendor.html.j2" %}
{% include "sections/05_cwe.html.j2" %}
{% include "sections/06_queries.html.j2" %}
{% include "sections/07_limitations.html.j2" %}
```

两个人分别写自己的 section，不会修改同一个模板。

## 报告必须做到离线可用

Plotly 建议：

```python
plotly.io.to_html(
    figure,
    full_html=False,
    include_plotlyjs=False,
)
```

然后在主报告中只内嵌一次 Plotly JS：

```python
include_plotlyjs="inline"
```

最终 HTML 不依赖 CDN，断网也能打开和交互。

---

# 七、双线并行分工

## A 线：数据基础、时间分析和报告骨架

### 负责人 A 负责

| 工作                    | 对应文件                                   |
| --------------------- | -------------------------------------- |
| 项目脚手架和配置              | `config.py`、`paths.py`、`analysis.yaml` |
| JSON 加载               | `loader.py`                            |
| SHA 和数据验证             | `validator.py`                         |
| 统一 prepared DataFrame | `prepare.py`                           |
| 时间分析                  | `temporal.py`                          |
| 勒索软件分析                | `ransomware.py`                        |
| 时间类图表                 | `temporal_charts.py`                   |
| HTML 总模板和 CSS         | `report.html.j2`、`report.css`          |
| 模块 1、2 报告段落           | `02_data_quality`、`03_temporal`        |
| 主运行脚本                 | `run_pipeline.py`                      |
| 最终集成                  | 汇总所有模块                                 |

### A 线交付物

```text
kev_prepared.csv
validation_report.json
field_quality.csv
monthly_additions.csv
annual_additions.csv
deadline_*.csv
ransomware_*.csv
时间相关 Plotly Figures
HTML 报告主框架
```

---

## B 线：厂商、CWE、查询和专题图表

### 负责人 B 负责

| 工作           | 对应文件                              |
| ------------ | --------------------------------- |
| 厂商汇总         | `vendor.py`                       |
| 厂商—产品汇总      | `vendor.py`                       |
| CR5、CR10、HHI | `vendor.py`                       |
| 厂商类图表        | `vendor_charts.py`                |
| CWE 展开和汇总    | `cwe.py`                          |
| CWE 图表       | `cwe_charts.py`                   |
| `filter_kev` | `queries.py`                      |
| 三组查询案例       | `queries.py` 或配置文件                |
| 模块 3、4 报告段落  | `04_vendor`、`05_cwe`、`06_queries` |
| 对应单元测试       | vendor/CWE/query tests            |

### B 线交付物

```text
vendor_summary.csv
vendor_product_summary.csv
top30_vendor_products.csv
vendor_concentration.json
cwe_exploded.csv
cwe_summary.csv
cwe_by_year.csv
三组查询结果及 summary
厂商和 CWE Plotly Figures
模块 3、4 HTML section
```

---

# 八、两条线之间的边界

## A 提供给 B 的唯一核心输入

```python
prepared_df = prepare_data(raw_df)
```

B 不重新读取 JSON，也不自行创建另一套清洗逻辑。

B 只能依赖以下统一字段：

```text
11 个原始字段
vendor_clean
product_clean
date_added
due_date
deadline_days
year_added
month_added
```

## B 提供给 A 的唯一集成输出

```python
vendor_artifacts = run_vendor_analysis(prepared_df)
cwe_artifacts = run_cwe_analysis(prepared_df)
query_artifacts = run_query_cases(prepared_df)
```

A 不修改 B 内部算法，只把这些结果传给报告生成器：

```python
build_report(
    metadata=metadata,
    validation=validation_artifacts,
    temporal=temporal_artifacts,
    ransomware=ransomware_artifacts,
    vendor=vendor_artifacts,
    cwe=cwe_artifacts,
    queries=query_artifacts,
)
```

---

# 九、实际 Git 分支方案

## 第一步：共同完成 scaffold

先建立：

```text
chore/project-scaffold
```

内容只包括：

* 目录结构；
* `requirements.txt`；
* 配置；
* 空函数和接口；
* dataclass；
* 最小 `run_pipeline.py`；
* 报告空模板；
* README 运行说明。

合并进 `main` 后，两个人同时从新的 `main` 创建分支。

## 第二步：并行开发

A：

```text
feat/data-temporal-report
```

B：

```text
feat/vendor-cwe-query
```

## 文件所有权

A 不修改：

```text
vendor.py
cwe.py
queries.py
vendor_charts.py
cwe_charts.py
04_vendor.html.j2
05_cwe.html.j2
06_queries.html.j2
```

B 不修改：

```text
loader.py
validator.py
prepare.py
temporal.py
ransomware.py
report.html.j2
report.css
run_pipeline.py
```

需要修改公共接口时，先在一个小 PR 中修改，不要两个人各自改变函数签名。

## 第三步：合并顺序

1. A 先合并基础数据层；
2. B 把分支 rebase 到最新 `main`；
3. B 合并厂商/CWE/查询模块；
4. A 作为集成人统一接入 `run_pipeline.py`；
5. 两人交叉测试；
6. 最后生成完整 HTML。

---

# 十、交叉检验方案

不能只测试“代码能运行”，还需要检查结果逻辑。

## A 检查 B

重点检查：

* `share` 是否使用 1,656 作为分母；
* 占比是否保存为小数；
* HHI 是否平方小数比例；
* vendor-product 排序是否稳定；
* 多值 CWE 是否正确展开；
* CWE 是否按 CVE 去重计数；
* 组合查询是否使用 AND；
* 查询是否没有修改原 DataFrame。

## B 检查 A

重点检查：

* 顶层 `count` 是否和记录数相等；
* 原始字段是否被保留；
* 空 CWE 是否未被删除；
* vendor/product 是否只做 `strip()`；
* 日期月份序列是否连续；
* 2021、2026 是否标记为不完整年份；
* `deadline_days` 是否为 `dueDate-dateAdded`；
* Known/Unknown 统计是否使用固定枚举；
* 报告中的结论是否超出数据边界。

---

# 十一、关键单元测试

特别是 `filter_kev`，建议至少写以下测试：

```python
def test_date_filter_is_closed_interval():
    ...


def test_vendor_filter_is_case_insensitive():
    ...


def test_vendor_filter_uses_substring():
    ...


def test_invalid_ransomware_raises_value_error():
    ...


def test_cwe_filter_is_exact_match():
    ...


def test_all_conditions_use_and():
    ...


def test_filter_does_not_mutate_input():
    ...


def test_result_sort_order():
    ...
```

集中度测试：

```python
def test_cr5_uses_decimal_share():
    ...


def test_hhi_uses_squared_decimal_share():
    ...
```

CWE 测试：

```python
def test_empty_cwe_records_are_not_filled():
    ...


def test_multiple_cwes_are_exploded():
    ...


def test_cwe_count_uses_unique_cve():
    ...
```

---

# 十二、运行入口

最终只保留一个完整运行命令：

```bash
python scripts/run_pipeline.py \
    --input data/CISA_KEV_2026-07-29.json \
    --output outputs \
    --report report/output/kev_report.html
```

流程应依次完成：

```text
1. SHA-256 校验
2. JSON 读取
3. 数据验证
4. 数据清洗
5. 模块 2 分析
6. 模块 3 分析
7. 模块 4 分析
8. CSV/JSON 导出
9. 图表生成
10. HTML 报告生成
11. 输出运行摘要
```

最终终端输出建议为：

```text
[PASS] SHA-256 verified
[PASS] Loaded 1,656 records
[PASS] Schema validation completed
[PASS] Prepared dataset exported
[PASS] Temporal analysis completed
[PASS] Vendor analysis completed
[PASS] CWE analysis completed
[PASS] Query cases completed
[PASS] HTML report generated:
       report/output/kev_report.html
```

## 最合理的最终分工结论

**A 线：公共基础设施 + 模块 1 + 模块 2 + HTML 报告引擎 + 最终集成。**

**B 线：模块 3 + 模块 4 + 对应图表 + 三组查询案例。**

这样两个人各自承担两个 20 分模块；A 多承担公共框架和集成，B 多承担厂商、CWE、查询与专题图表，整体工作量基本平衡，而且文件冲突最少。

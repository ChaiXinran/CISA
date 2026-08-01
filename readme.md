# CISA KEV 数据分析大作业

本仓库用于完成课程大作业第 3 题：**CISA Known Exploited Vulnerabilities Catalog Analysis**。

项目基于课程提供的 CISA 已知被利用漏洞目录（Known Exploited Vulnerabilities，KEV）冻结快照，对漏洞记录进行数据验证、统计分析、可视化和组合查询，并最终生成一份可离线打开的 **HTML 交互式报告**。

本项目不实现 GUI，计划完成题目要求中除 GUI 以外的全部内容。

---

## 1. 项目目标

本项目主要完成以下四部分工作：

1. **数据读取、验证与预处理**

   * 读取课程提供的 KEV JSON 数据；
   * 验证文件完整性、字段结构、CVE 编号、日期和数据类型；
   * 保留原始字段，并建立规范化后的辅助字段；
   * 导出可复用的中间数据和验证结果。

2. **时间、期限与勒索软件分析**

   * 分析 KEV 记录随月份和年份的变化；
   * 分析 `dateAdded` 与 `dueDate` 之间的处置期限；
   * 比较 `Known` 和 `Unknown` 勒索软件活动标记。

3. **厂商、产品与集中度分析**

   * 统计厂商及厂商—产品组合的 KEV 记录数量；
   * 计算占比、累计占比、CR5、CR10 和 HHI；
   * 比较不同厂商记录中的勒索软件活动标记。

4. **CWE 分析与组合查询**

   * 展开一条 CVE 对应的多个 CWE；
   * 统计主要 CWE 及其年度分布；
   * 实现日期、厂商、勒索软件标记和 CWE 的组合筛选；
   * 导出查询结果和查询摘要。

最终结果将整理为一个包含交互式图表、统计表格、查询案例和结论说明的 HTML 报告。

---

## 2. 从哪里查找项目资料

### 作业要求

课程大作业的完整题目要求位于：

```text
docs/Question_3_CISA_KEV.md
```

课程提供的报告模板位于：

```text
docs/大作业模板.docx
```

### 数据集

本项目使用的唯一数据文件位于：

```text
data/CISA_KEV_2026-07-29.json
```

该文件是 CISA KEV Catalog 的冻结快照，包含 1,656 条漏洞记录。

数据集版本、来源、字段结构、SHA-256、清洗边界和使用限制请查看：

```text
data/数据说明.txt
```

在开始编写分析代码前，应先阅读该文件。

---

## 3. 重要数据说明

每条漏洞记录包含以下字段：

```text
cveID
vendorProject
product
vulnerabilityName
dateAdded
shortDescription
requiredAction
dueDate
knownRansomwareCampaignUse
notes
cwes
```

分析时需要注意：

* `dateAdded` 表示漏洞加入 KEV 目录的日期，不是漏洞披露日期或首次攻击日期；
* `dueDate` 表示目录中要求完成处置的截止日期，不代表实际修复耗时；
* `knownRansomwareCampaignUse` 只有 `Known` 和 `Unknown`；
* `Unknown` 不表示该漏洞没有被利用，只表示尚无经确认的勒索软件活动利用信息；
* `cwes` 是列表，一条 CVE 可以对应多个 CWE；
* 部分记录的 `cwes` 是空列表，不得删除或随意填充；
* 厂商和产品字段中的首尾空格只能通过 `str.strip()` 建立清洗列；
* 不进行模糊厂商合并；
* 原始字段必须保留，不能被清洗字段覆盖；
* KEV 不包含市场占有率、资产数量、攻击次数、CVSS 或 EPSS；
* 不能仅根据 KEV 记录数量评价厂商或产品的安全性。

---

## 4. 计划中的仓库结构

```text
CISA/
├── data/                         # 原始数据和数据说明
│   ├── CISA_KEV_2026-07-29.json
│   └── 数据说明.txt
│
├── docs/                         # 作业要求和课程模板
│   ├── 大作业_en.pdf
│   └── 大作业模板.docx
│
├── src/
│   └── kev_analysis/
│       ├── data/                 # 数据读取、验证和预处理
│       ├── analysis/             # 各项统计分析和查询
│       ├── visualization/        # Plotly 交互式图表
│       ├── reporting/            # HTML 报告生成
│       └── utils/                # 路径、日志和导出工具
│
├── scripts/
│   ├── run_pipeline.py           # 完整分析流程入口
│   └── verify_outputs.py         # 输出结果检查
│
├── report/
│   ├── templates/                # Jinja2 HTML 模板
│   ├── assets/                   # CSS 等静态资源
│   └── output/                   # 最终 HTML 报告
│
├── outputs/
│   ├── prepared/                 # 清洗后的中间数据
│   ├── tables/                   # 分析表格
│   ├── figures/                  # 图表或图表配置
│   ├── queries/                  # 查询结果
│   ├── metrics/                  # 指标和验证报告
│   └── logs/                     # 运行日志
│
├── tests/                        # 单元测试
├── config/                       # 分析配置
├── requirements.txt              # Python 依赖
├── pyproject.toml
└── README.md
```

具体模块仍在开发中，实际目录可能随实现进度进行小幅调整。

---

## 5. 技术方案

计划使用以下 Python 工具：

* `pandas`：数据读取、清洗和统计；
* `numpy`：数值计算；
* `plotly`：交互式图表；
* `jinja2`：HTML 报告模板；
* `pytest`：单元测试；
* `PyYAML`：读取分析配置。

最终报告采用静态 HTML 形式，不依赖 Dash、Flask 或 Streamlit 服务。报告生成后应能直接在浏览器中离线打开。

---

## 6. 环境准备

建议使用 Python 3.10 或更高版本。

创建虚拟环境：

```bash
python -m venv .venv
```

Windows：

```bash
.venv\Scripts\activate
```

Linux / macOS：

```bash
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

如果项目尚未提供 `requirements.txt`，开发阶段至少需要安装：

```bash
pip install pandas numpy plotly jinja2 pyyaml pytest
```

---

## 7. 如何运行

> 以下命令为项目计划中的统一入口。代码完成后以实际脚本参数为准。

在仓库根目录运行：

```bash
python scripts/run_pipeline.py \
    --input data/CISA_KEV_2026-07-29.json \
    --output outputs \
    --report report/output/kev_report.html
```

在 Windows PowerShell 中也可以写成单行：

```powershell
python scripts/run_pipeline.py --input data/CISA_KEV_2026-07-29.json --output outputs --report report/output/kev_report.html
```

完整流程预计包括：

1. 验证输入文件 SHA-256；
2. 读取 JSON；
3. 检查数据结构和字段；
4. 生成规范化中间数据；
5. 执行时间、期限和勒索软件分析；
6. 执行厂商、产品和集中度分析；
7. 执行 CWE 分析；
8. 执行预设组合查询；
9. 导出 CSV 和 JSON 结果；
10. 生成 HTML 交互式报告。

最终报告预计位于：

```text
report/output/kev_report.html
```

使用浏览器直接打开即可查看。

---

## 8. 输出文件说明

### 清洗后的数据

```text
outputs/prepared/
```

存放统一预处理后的 KEV 数据和展开后的 CWE 数据。

### 统计表格

```text
outputs/tables/
```

可能包括：

```text
field_quality.csv
monthly_additions.csv
annual_additions.csv
deadline_summary.csv
ransomware_summary.csv
vendor_summary.csv
vendor_product_summary.csv
cwe_summary.csv
cwe_by_year.csv
```

### 指标和验证结果

```text
outputs/metrics/
```

可能包括：

```text
catalog_metadata.json
validation_report.json
vendor_concentration.json
```

### 组合查询结果

```text
outputs/queries/
```

每组查询应同时导出：

```text
query_XX_results.csv
query_XX_summary.json
```

### 最终报告

```text
report/output/kev_report.html
```

---

## 9. 测试

运行全部测试：

```bash
pytest
```

或显示更详细的信息：

```bash
pytest -v
```

测试重点包括：

* JSON 顶层结构；
* CVE 编号唯一性；
* 日期解析和先后关系；
* 原始字段是否保留；
* 厂商和产品清洗是否只使用 `strip()`；
* 多值 CWE 是否正确展开；
* CR5、CR10 和 HHI 是否使用小数比例计算；
* 组合查询是否使用 AND 连接；
* 日期查询是否为闭区间；
* 厂商查询是否大小写不敏感；
* CWE 查询是否进行完整值匹配；
* 查询函数是否修改原始 DataFrame；
* 输出排序是否稳定。

---

## 10. 协作分工

项目采用两条开发线并行完成。

### 开发线 A

负责：

* 项目基础结构；
* 数据读取、验证和预处理；
* 时间趋势分析；
* 截止期限分析；
* 勒索软件标记分析；
* HTML 报告主框架；
* 最终运行脚本和项目集成。

主要代码目录：

```text
src/kev_analysis/data/
src/kev_analysis/analysis/temporal.py
src/kev_analysis/analysis/ransomware.py
src/kev_analysis/visualization/temporal_charts.py
src/kev_analysis/reporting/
scripts/run_pipeline.py
```

### 开发线 B

负责：

* 厂商和产品统计；
* CR5、CR10 和 HHI；
* CWE 展开与统计；
* 组合查询函数；
* 厂商和 CWE 图表；
* 查询案例和对应测试。

主要代码目录：

```text
src/kev_analysis/analysis/vendor.py
src/kev_analysis/analysis/cwe.py
src/kev_analysis/analysis/queries.py
src/kev_analysis/visualization/vendor_charts.py
src/kev_analysis/visualization/cwe_charts.py
```

两条开发线共同使用统一的预处理数据，避免各自实现不同的数据清洗逻辑。

---

## 11. Git 协作建议

建议使用以下分支：

```text
main
chore/project-scaffold
feat/data-temporal-report
feat/vendor-cwe-query
```

开发流程：

1. 先完成并合并项目基础结构；
2. 两名成员分别创建功能分支；
3. 每个模块通过 Pull Request 合并；
4. 不直接在 `main` 上开发；
5. 提交前运行相关测试；
6. 合并后运行完整分析流程；
7. 最终交叉检查统计结果和报告结论。

提交信息示例：

```text
feat: add KEV JSON loader
feat: implement vendor concentration analysis
test: add query filter tests
fix: preserve empty CWE lists
docs: update project README
```

---

## 12. 结果解释边界

报告中的结论只能描述课程数据本身，例如：

* 哪些厂商标签在 KEV 目录中出现较多；
* 某些 CWE 在目录记录中的分布；
* KEV 加入记录在不同月份或年份的变化；
* 目录规定的处置期限分布；
* `Known` 和 `Unknown` 标签的统计差异。

不得根据本数据直接推断：

* 某厂商比其他厂商更不安全；
* 某产品更容易遭到攻击；
* 某漏洞的真实攻击次数；
* 所有机构实际完成修复所需的时间；
* 漏洞的完整风险等级；
* 厂商的真实漏洞率或受攻击概率。

这些限制应在最终 HTML 报告中明确说明。

---

## 13. 当前状态

当前仓库已经提供：

* 课程大作业要求；
* 课程报告模板；
* CISA KEV 冻结快照；
* 数据集说明。

代码、测试和 HTML 报告正在开发中。

在参与开发前，请依次阅读：

```text
README.md
docs/大作业_en.pdf
data/数据说明.txt
```

然后根据所负责的模块查看 `src/kev_analysis/` 下的对应代码。

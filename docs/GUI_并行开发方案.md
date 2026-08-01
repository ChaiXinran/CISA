# KEV GUI 基础框架与两人并行开发方案

## 1. 当前基础框架

GUI 使用 PyQt6，并直接读取课程 JSON。目前已提供：

- 文件选择、完整验证、版本/发布日期/记录数显示；
- 日期、厂商、产品、Known/Unknown、CWE 组合筛选与重置；
- CVE 结果表和详情；
- 当前结果 CSV 导出；
- 可视化统一更新与 PNG 导出接口；
- 独立启动入口。

```powershell
conda activate csia
python scripts/run_gui.py
```

## 2. 唯一公共数据流

```text
课程 JSON
  → load_catalog → validate_catalog → prepare_data
  → GuiState.prepared_df
  → filter_kev（全部条件 AND）
  → GuiState.filtered_df
      ├── ResultsTable.update_data
      ├── VisualizationPanel.update_data
      └── CSV 导出
```

GUI 组件不得重新读取 JSON，也不得自行建立另一套清洗或筛选逻辑。

## 3. 已固定的可视化契约

负责人 B 提供的可视化容器必须实现：

```python
def update_data(self, filtered_df: pd.DataFrame) -> None: ...
def export_png(self, path: str | Path) -> None: ...
```

主窗口只调用这两个接口，不依赖 3D 地球内部实现。组件不得修改传入的 DataFrame。

公共状态 `GuiState` 包含：

```text
metadata, raw_df, prepared_df, filtered_df,
active_filters, selected_cve
```

## 4. 两人分工

### 负责人 A：GUI 核心与数据交互

分支：`feat/gui-core`

负责文件：

```text
src/kev_analysis/gui/main_window.py
src/kev_analysis/gui/filter_panel.py
src/kev_analysis/gui/results_table.py
src/kev_analysis/gui/detail_panel.py
src/kev_analysis/gui/state.py
scripts/run_gui.py
tests/test_gui.py
```

负责内容：

- 主窗口、标签页和状态流转；
- 文件加载、错误反馈和元数据；
- 筛选、重置和空结果；
- CVE 表格、详情和 CSV 导出；
- GUI 核心测试；
- 最终组件接入。

### 负责人 B：3D 地球与联动图表

分支：`feat/gui-visualization`

新建或主要负责：

```text
src/kev_analysis/gui/globe_view.py
src/kev_analysis/gui/chart_panel.py
src/kev_analysis/gui/chart_export.py
src/kev_analysis/gui/web_bridge.py
data/vendor_locations.csv
tests/test_gui_visualization.py
```

负责内容：

- PyQt6 WebEngine 中的 3D 地球；
- 厂商地理映射表和来源；
- 地图点、光柱、悬停和点击联动；
- 月度趋势及厂商/CWE 图，至少两张随筛选联动；
- PNG 导出；
- 未映射厂商和空结果显示；
- 可视化测试。

B 不直接修改 `main_window.py`，完成组件后由 A 接入当前 `VisualizationPanel` 位置。

## 5. 地图口径

地图只能表示厂商总部或统一选定的登记地，不能表示漏洞发生地、攻击地点、设备所在地或受害组织所在地。

推荐标题：

> 按厂商总部所在地映射的 KEV 厂商标签记录

位置表至少包含：

```text
vendor_clean,country,city,latitude,longitude,location_type,source
```

要求：

- 每个位置保留来源；
- 未确认位置保留为 unmapped，不得猜测；
- 跨国厂商统一采用全球总部口径；
- 显示已映射和未映射记录数；
- 点大小可表示当前筛选结果的 KEV 记录数；
- 颜色可表示 Known 占比；
- 不得称为“全球攻击分布”或“全球漏洞发生分布”。

## 6. 合并顺序

1. 合并当前公共框架；
2. 两人从同一提交创建各自分支；
3. A 完善核心交互，B 独立开发可视化；
4. B 提交符合契约的组件和测试；
5. A 将组件接入标签页和 PNG 导出按钮；
6. 两人共同完成端到端验收；
7. 更新 README 和最终报告说明。

## 7. 最终验收清单

- 直接读取课程 JSON；
- 显示版本、发布日期、记录数和状态；
- 日期闭区间，厂商/产品大小写不敏感子串匹配；
- Known/Unknown 和 CWE 完整值筛选；
- 所有条件使用 AND，重置后恢复 1,656 条；
- 至少两张规定图表随筛选更新；
- 3D 地球使用同一份 `filtered_df`；
- CVE 表格和详情正确，空结果不崩溃；
- 当前结果导出 CSV，当前图表导出 PNG；
- 显示未映射厂商数量；
- 地图不被解释为漏洞或攻击发生地；
- 全部自动化测试通过。

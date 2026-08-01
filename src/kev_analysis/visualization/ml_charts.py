"""Interactive Plotly figures for exploratory clustering."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

FEATURE_LABELS = {
    "deadline_days": "处置期限", "year_added": "加入年份",
    "is_known_ransomware": "Known 比例", "cwe_count": "CWE 数量",
    "has_cwe": "提供 CWE", "vendor_frequency": "厂商频数",
    "product_frequency": "产品频数",
}
COLORS = ["#00A6A6", "#F05D5E", "#6C63FF", "#F2A541", "#2D7DD2", "#7A9E35", "#C855A1", "#657786"]


def build_ml_figures(
    assignments: pd.DataFrame,
    profiles: pd.DataFrame,
    standardized_profiles: pd.DataFrame,
    k_selection: pd.DataFrame,
    metrics: dict,
) -> dict[str, go.Figure]:
    selected_k = metrics["selected_k"]
    selection = go.Figure()
    selection.add_scatter(
        x=k_selection["k"], y=k_selection["silhouette_score"], mode="lines+markers",
        name="轮廓系数", line={"color": COLORS[0], "width": 3}, marker={"size": 10},
    )
    selection.add_bar(
        x=k_selection["k"], y=k_selection["inertia"], name="簇内平方和",
        marker_color="#d7e2ea", opacity=.65, yaxis="y2",
    )
    selection.add_vline(x=selected_k, line_dash="dash", line_color=COLORS[1])
    selection.add_annotation(x=selected_k, y=1, yref="paper", text=f"选择 k={selected_k}", showarrow=False)
    selection.update_layout(
        title="聚类数选择：轮廓系数与簇内平方和", xaxis_title="聚类数 k",
        yaxis={"title": "轮廓系数"},
        yaxis2={"title": "簇内平方和", "overlaying": "y", "side": "right", "showgrid": False},
        barmode="overlay",
    )

    plot_data = assignments.copy()
    plot_data["cluster_label"] = plot_data["cluster"].map(lambda value: f"簇 {value}")
    scatter = px.scatter(
        plot_data, x="pca_1", y="pca_2", color="cluster_label", hover_name="cveID",
        hover_data=["vendor_clean", "product_clean", "deadline_days", "cwe_count"],
        color_discrete_sequence=COLORS, opacity=.68,
        labels={"pca_1": "PCA 1", "pca_2": "PCA 2", "cluster_label": "聚类"},
        title="PCA 二维投影：KEV 目录结构分组",
    )
    scatter.update_traces(marker={"size": 7, "line": {"width": .35, "color": "white"}})
    scatter_3d = px.scatter_3d(
        plot_data, x="pca_1", y="pca_2", z="pca_3", color="cluster_label",
        hover_name="cveID", hover_data=["vendor_clean", "product_clean", "knownRansomwareCampaignUse"],
        color_discrete_sequence=COLORS, opacity=.72,
        labels={"cluster_label": "聚类"}, title="PCA 三维星云：旋转探索聚类结构",
    )
    scatter_3d.update_traces(marker={"size": 4})
    scatter_3d.update_layout(scene={"xaxis_title": "PCA 1", "yaxis_title": "PCA 2", "zaxis_title": "PCA 3"})

    heat = standardized_profiles.set_index("cluster")
    heatmap = go.Figure(go.Heatmap(
        z=heat[list(FEATURE_LABELS)].to_numpy(), x=list(FEATURE_LABELS.values()),
        y=[f"簇 {value}" for value in heat.index],
        colorscale=[[0, "#274c77"], [.5, "#f7f7f2"], [1, "#d1495b"]], zmid=0,
        colorbar={"title": "标准化均值"}, hovertemplate="%{y}<br>%{x}: %{z:.2f}<extra></extra>",
    ))
    heatmap.update_layout(title="聚类特征指纹热力图")

    radar = go.Figure()
    feature_names = list(FEATURE_LABELS)
    for index, row in standardized_profiles.iterrows():
        values = [row[column] for column in feature_names]
        radar.add_scatterpolar(
            r=values + [values[0]], theta=list(FEATURE_LABELS.values()) + [next(iter(FEATURE_LABELS.values()))],
            fill="toself", opacity=.45, name=f"簇 {int(row['cluster'])}",
            line={"color": COLORS[index % len(COLORS)], "width": 2},
        )
    radar.update_layout(title="聚类特征雷达轮廓", polar={"radialaxis": {"visible": True}})

    size_chart = go.Figure(go.Pie(
        labels=[f"簇 {value}" for value in profiles["cluster"]], values=profiles["record_count"],
        hole=.58, marker={"colors": COLORS[:len(profiles)]}, textinfo="label+percent",
        hovertemplate="%{label}<br>%{value} 条<br>%{percent}<extra></extra>",
    ))
    size_chart.update_layout(title="聚类规模构成", annotations=[{
        "text": f"k={selected_k}", "x": .5, "y": .5, "showarrow": False, "font": {"size": 22}
    }])
    figures = (selection, scatter, scatter_3d, heatmap, radar, size_chart)
    for figure in figures:
        figure.update_layout(template="plotly_white", legend_title_text="聚类")
    return dict(zip(
        ["ml_k_selection", "ml_pca_scatter", "ml_pca_3d", "ml_profile_heatmap", "ml_profile_radar", "ml_cluster_sizes"],
        figures, strict=True,
    ))

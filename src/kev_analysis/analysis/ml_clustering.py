"""Exploratory K-means clustering of KEV catalog-record structure."""

from __future__ import annotations

import os
import warnings

os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count() or 1))
warnings.filterwarnings(
    "ignore", category=UserWarning,
    module=r"joblib\.externals\.loky\.backend\.context",
)

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from kev_analysis.models import AnalysisArtifacts

FEATURE_COLUMNS = [
    "deadline_days", "year_added", "is_known_ransomware", "cwe_count",
    "has_cwe", "vendor_frequency", "product_frequency",
]
MODEL_FEATURE_COLUMNS = [column for column in FEATURE_COLUMNS if column != "has_cwe"]


def build_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create deterministic numeric features without ordinal-encoding labels."""
    required = {
        "cveID", "vendor_clean", "product_clean", "deadline_days", "year_added",
        "knownRansomwareCampaignUse", "cwes",
    }
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"Missing prepared columns for ML analysis: {missing}")
    features = pd.DataFrame(index=df.index)
    features["deadline_days"] = pd.to_numeric(df["deadline_days"], errors="raise")
    features["year_added"] = pd.to_numeric(df["year_added"], errors="raise")
    features["is_known_ransomware"] = df["knownRansomwareCampaignUse"].eq("Known").astype("int64")
    features["cwe_count"] = df["cwes"].map(lambda value: len(value) if isinstance(value, list) else 0)
    features["has_cwe"] = features["cwe_count"].gt(0).astype("int64")
    vendor_counts = df["vendor_clean"].value_counts()
    product_counts = df.groupby(["vendor_clean", "product_clean"]).size()
    features["vendor_frequency"] = df["vendor_clean"].map(vendor_counts).astype("int64")
    features["product_frequency"] = [
        int(product_counts.loc[(vendor, product)])
        for vendor, product in zip(df["vendor_clean"], df["product_clean"], strict=True)
    ]
    if features.isna().any().any():
        raise ValueError("ML feature construction produced null values")
    return features[FEATURE_COLUMNS]


def select_cluster_count(
    scaled_features: np.ndarray,
    k_values: range = range(2, 9),
    random_state: int = 42,
) -> tuple[pd.DataFrame, int]:
    """Evaluate candidate k values using silhouette score and inertia."""
    rows = []
    for k in k_values:
        model = KMeans(n_clusters=k, random_state=random_state, n_init=20)
        labels = model.fit_predict(scaled_features)
        rows.append({
            "k": k,
            "silhouette_score": float(silhouette_score(scaled_features, labels)),
            "inertia": float(model.inertia_),
        })
    selection = pd.DataFrame(rows).sort_values("k").reset_index(drop=True)
    best = selection.sort_values(["silhouette_score", "k"], ascending=[False, True]).iloc[0]
    return selection, int(best["k"])


def run_ml_clustering(df: pd.DataFrame, random_state: int = 42) -> AnalysisArtifacts:
    """Run feature construction, k selection, K-means, PCA and profiling."""
    features = build_ml_features(df)
    descriptive_features = features.copy()
    for column in ("vendor_frequency", "product_frequency"):
        descriptive_features[column] = np.log1p(descriptive_features[column])
    # has_cwe is exactly derived from cwe_count. Excluding it from the distance
    # matrix avoids double-weighting missing CWE data, while retaining it in
    # exported profiles for interpretation.
    scaled = StandardScaler().fit_transform(descriptive_features[MODEL_FEATURE_COLUMNS])
    descriptive_scaled = StandardScaler().fit_transform(descriptive_features[FEATURE_COLUMNS])
    k_selection, selected_k = select_cluster_count(scaled, random_state=random_state)
    model = KMeans(n_clusters=selected_k, random_state=random_state, n_init=20)
    labels = model.fit_predict(scaled)
    pca = PCA(n_components=3, random_state=random_state)
    coordinates = pca.fit_transform(scaled)

    assignments = df[["cveID", "vendor_clean", "product_clean", "knownRansomwareCampaignUse"]].copy()
    assignments = pd.concat([assignments.reset_index(drop=True), features.reset_index(drop=True)], axis=1)
    assignments["cluster"] = labels.astype("int64") + 1
    assignments[["pca_1", "pca_2", "pca_3"]] = coordinates
    profiles = assignments.groupby("cluster", sort=True)[FEATURE_COLUMNS].mean().reset_index()
    sizes = assignments["cluster"].value_counts().sort_index()
    profiles.insert(1, "record_count", profiles["cluster"].map(sizes).astype("int64"))
    profiles.insert(2, "record_share", profiles["record_count"] / len(assignments))
    standardized_profiles = (
        pd.DataFrame(descriptive_scaled, columns=FEATURE_COLUMNS)
        .assign(cluster=assignments["cluster"].to_numpy())
        .groupby("cluster").mean().reset_index()
    )
    metrics = {
        "selected_k": selected_k,
        "best_silhouette_score": float(
            k_selection.loc[k_selection["k"].eq(selected_k), "silhouette_score"].iloc[0]
        ),
        "random_state": random_state,
        "feature_columns": FEATURE_COLUMNS,
        "model_feature_columns": MODEL_FEATURE_COLUMNS,
        "pca_explained_variance_ratio": [float(value) for value in pca.explained_variance_ratio_],
        "pca_explained_variance_total": float(pca.explained_variance_ratio_.sum()),
    }
    from kev_analysis.visualization.ml_charts import build_ml_figures
    return AnalysisArtifacts(
        tables={
            "cluster_assignments": assignments,
            "cluster_profiles": profiles,
            "cluster_profiles_standardized": standardized_profiles,
            "k_selection": k_selection,
        },
        metrics=metrics,
        figures=build_ml_figures(assignments, profiles, standardized_profiles, k_selection, metrics),
        notes=[
            "Clusters describe catalog-record structure, not vulnerability risk or attack probability.",
            "Unknown is an unconfirmed label, not evidence of no ransomware use.",
            "Vendor and product names use frequencies, not arbitrary ordinal codes.",
        ],
    )

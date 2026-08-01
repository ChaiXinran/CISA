from pathlib import Path

import pytest

from kev_analysis.analysis.ml_clustering import FEATURE_COLUMNS, MODEL_FEATURE_COLUMNS, build_ml_features, run_ml_clustering
from kev_analysis.data import load_catalog, prepare_data


@pytest.fixture(scope="module")
def full_prepared():
    root = Path(__file__).resolve().parents[1]
    _, raw = load_catalog(root / "data/CISA_KEV_2026-07-29.json")
    return prepare_data(raw)


@pytest.fixture(scope="module")
def ml_result(full_prepared):
    return run_ml_clustering(full_prepared)


def test_features_are_complete_and_numeric(full_prepared):
    features = build_ml_features(full_prepared)
    assert list(features.columns) == FEATURE_COLUMNS
    assert features.shape == (1656, 7)
    assert not features.isna().any().any()
    assert features["is_known_ransomware"].sum() == 332
    assert features["has_cwe"].sum() == 1485
    assert "has_cwe" not in MODEL_FEATURE_COLUMNS


def test_k_selection_and_assignments_reconcile(ml_result):
    selection = ml_result.tables["k_selection"]
    assignments = ml_result.tables["cluster_assignments"]
    profiles = ml_result.tables["cluster_profiles"]
    selected_k = ml_result.metrics["selected_k"]
    assert list(selection["k"]) == list(range(2, 9))
    assert selection["silhouette_score"].between(-1, 1).all()
    assert selected_k == selection.loc[selection["silhouette_score"].idxmax(), "k"]
    assert len(assignments) == 1656
    assert assignments["cluster"].nunique() == selected_k
    assert profiles["record_count"].sum() == 1656
    assert profiles["record_share"].sum() == pytest.approx(1.0)
    characteristics = ml_result.tables["cluster_characteristics"]
    assert len(characteristics) == selected_k
    assert characteristics["title"].str.len().gt(0).all()
    assert characteristics["description"].str.contains("Known").all()


def test_ml_is_deterministic_and_figures_complete(full_prepared, ml_result):
    repeated = run_ml_clustering(full_prepared)
    assert repeated.metrics["selected_k"] == ml_result.metrics["selected_k"]
    assert repeated.tables["cluster_assignments"]["cluster"].equals(
        ml_result.tables["cluster_assignments"]["cluster"]
    )
    assert set(ml_result.figures) == {
        "ml_k_selection", "ml_pca_scatter", "ml_pca_3d",
        "ml_profile_heatmap", "ml_feature_deviation", "ml_profile_radar", "ml_cluster_sizes",
    }

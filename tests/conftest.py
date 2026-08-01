from pathlib import Path
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))


@pytest.fixture
def prepared_df():
    rows = [
        ("CVE-2025-0001", "Acme", "One", "2025-01-01", "Known", ["CWE-79", "CWE-89"]),
        ("CVE-2025-0002", "acme Labs", "Two", "2025-01-31", "Unknown", ["CWE-79"]),
        ("CVE-2024-0003", "Beta", "One", "2024-12-31", "Known", []),
        ("CVE-2025-0004", "Beta", "Three", "2025-01-31", "Unknown", ["CWE-789"]),
    ]
    return pd.DataFrame([
        {
            "cveID": cve, "vendorProject": vendor, "product": product,
            "vendor_clean": vendor, "product_clean": product,
            "dateAdded": date, "date_added": pd.Timestamp(date),
            "year_added": int(date[:4]), "knownRansomwareCampaignUse": flag, "cwes": cwes,
        }
        for cve, vendor, product, date, flag, cwes in rows
    ])

"""Shared constants for the frozen course dataset."""

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

TOP_LEVEL_FIELDS = {
    "title",
    "catalogVersion",
    "dateReleased",
    "count",
    "vulnerabilities",
}

EXPECTED_RECORD_COUNT = 1656
EXPECTED_SHA256 = "15B44D7C9C57F3D27128999E09F0FC991659A0B64713B5E1AF599565447A2409"
RANSOMWARE_VALUES = {"Known", "Unknown"}


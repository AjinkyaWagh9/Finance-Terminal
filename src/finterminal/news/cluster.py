# Tune these based on manual inspection of the first 3 runs.
# CLUSTER_DISTANCE_THRESHOLD: lower → more smaller clusters; higher → fewer bigger clusters.
# MINHASH_JACCARD_THRESHOLD: imported by dedupe.py — set here so all thresholds are together.
# LINEAGE_CENTROID_THRESHOLD: imported by lineage.py.
CLUSTER_DISTANCE_THRESHOLD: float = 0.25
MINHASH_JACCARD_THRESHOLD: float = 0.85
LINEAGE_CENTROID_THRESHOLD: float = 0.70

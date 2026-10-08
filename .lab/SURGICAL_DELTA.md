# MainV2 Lab — audited surgical delta

## Inherited source
- **Imported from:** SouthPaw302/AIVideoEdit MainV2
- **Exact SHA:** `316fe96c7316d76d14308d5f27293e071aa20943`
- **Snapshot proof:** `.lab/MIRROR_RECEIPT.json` (238 source files identical at import; 13 workflow YAMLs preserved byte-for-byte, not enabled)

## Lab changes from upstream (do not silently upstream)
1. **`bootstrap.py`:** `clear_volatile_session_state` preserves `.aivideoedit/models` and `.aivideoedit/cache`; stale sessions/OS are still cleared. Previous source wiped the ONNX model directory immediately after provisioning, silently invoking the fallback analyzer instead of Beat This.
2. **`tests/test_lab_bootstrap_model_persistence.py`:** Regression test for repeated bootstrap and preserved ONNX model bytes.
3. **`.github/workflows/irish-eyes-real-song-proof.yml`:** The real-song runner verifies the primary Beat This model after bootstrap; any fallback is a blocking failure.
4. **`projects/irish-eyes-lab/` (song branch only):** Test song package and visual proof script built from source assets, not finished videos.

## Safety
All changes are **lab-only**. No pushes to the canonical AIVideoEdit repository, no promotion from lab to its Main. A successful workflow or MP4 render does **not** constitute visual acceptance.

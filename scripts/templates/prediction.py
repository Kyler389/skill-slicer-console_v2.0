"""
Template: ML prediction / inference workflow.

Usage:
    python run_slicer_script.py --mode run --script templates/prediction.py --module-paths "path/to/model_module"
"""
import slicer
import os, sys

output_dir = os.path.dirname(__file__) or "."

# ── Config ──────────────────────────────────────────────────────────────
model_node_name = None   # Set to a specific node name, or None for auto-detect
output_name = "PredictionResult"

# ── Locate input volume ────────────────────────────────────────────────
volumes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
if not volumes:
    print("ERROR: No volume node found for prediction.", file=sys.stderr)
    raise SystemExit(1)

input_volume = volumes[0]
if model_node_name:
    for v in volumes:
        if v.GetName() == model_node_name:
            input_volume = v
            break

print(f"[prediction] Input: {input_volume.GetName()}")
dims = input_volume.GetImageData().GetDimensions()
print(f"[prediction] Dimensions: {dims[0]} x {dims[1]} x {dims[2]}")

# ── Placeholder prediction logic ───────────────────────────────────────
# Replace with actual ML model inference:
#   model = slicer.modules.your_model.Logic()
#   result = model.predict(input_volume)
result_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", output_name)
result_node.SetAndObserveImageData(input_volume.GetImageData())
result_node.SetName(output_name)
print(f"[prediction] Output created: {output_name}")

# ── Save result ────────────────────────────────────────────────────────
output_path = os.path.join(output_dir, f"{output_name}.nrrd")
slicer.util.saveNode(result_node, output_path)
print(f"[prediction] Saved: {output_path}")

# ── Report ─────────────────────────────────────────────────────────────
result_file = os.environ.get("SLICER_RESULT_FILE")
if result_file:
    import json
    with open(result_file, "w") as f:
        json.dump({"output": output_path, "status": "ok"}, f)

print("[prediction] Done.")

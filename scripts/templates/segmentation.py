"""
Template: Volume segmentation workflow.

Usage:
    python run_slicer_script.py --mode run --script templates/segmentation.py --module-paths "path/to/modules"
"""
import slicer
import os

# ── Config ──────────────────────────────────────────────────────────────
volume_name = "InputVolume"       # Name of the volume node in the scene
output_dir = os.path.dirname(__file__) or "."

# ── Find or load volume ────────────────────────────────────────────────
volumes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
if not volumes:
    print("ERROR: No scalar volume found in the scene.", file=sys.stderr)
    raise SystemExit(1)

volume = volumes[0]
print(f"[segmentation] Using volume: {volume.GetName()} ({volume.GetID()})")

# ── Create segmentation ────────────────────────────────────────────────
seg_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Segmentation")
seg_node.CreateDefaultDisplayNodes()
seg_node.SetReferenceImageGeometryParameterFromVolumeNode(volume)

# Add a segment (example: threshold-based)
import vtk
threshold = vtk.vtkImageThreshold()
threshold.SetInputData(volume.GetImageData())
threshold.ThresholdBetween(100, 500)
threshold.SetInValue(1)
threshold.SetOutValue(0)
threshold.Update()

# Create segment
segment = seg_node.GetSegmentation().AddEmptySegment("Target", "TargetRegion")
seg_node.AddSegmentFromBinaryLabelmapRepresentation(
    threshold.GetOutput(), segment, None
)

print(f"[segmentation] Segment created successfully.")

# ── Save ────────────────────────────────────────────────────────────────
output_path = os.path.join(output_dir, "segmentation.seg.nrrd")
slicer.util.saveNode(seg_node, output_path)
print(f"[segmentation] Saved: {output_path}")

# Write result via SLICER_RESULT_FILE if available
result_file = os.environ.get("SLICER_RESULT_FILE")
if result_file:
    import json
    with open(result_file, "w") as f:
        json.dump({"segmentation": output_path, "segments": 1}, f)

print("[segmentation] Done.")

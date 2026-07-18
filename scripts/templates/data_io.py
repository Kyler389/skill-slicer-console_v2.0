"""
Template: Data import/export workflow.

Usage:
    python run_slicer_script.py --mode run --script templates/data_io.py
"""
import slicer
import os, sys

output_dir = os.path.dirname(__file__) or "."

def list_scene():
    """Print all nodes in the scene."""
    print("[data_io] Scene contents:")
    for i in range(slicer.mrmlScene.GetNumberOfNodes()):
        node = slicer.mrmlScene.GetNthNode(i)
        print(f"  [{node.GetID()}] {node.GetName()} ({node.GetClassName()})")

def export_volume(volume_node, filepath):
    """Export a volume node to NRRD or NIFTI."""
    slicer.util.saveNode(volume_node, filepath)
    print(f"[data_io] Exported: {filepath}")

def import_volume(filepath):
    """Import a volume from file."""
    node = slicer.util.loadVolume(filepath)
    if node:
        print(f"[data_io] Imported: {node.GetName()} from {filepath}")
    return node

# ── Example: list everything ──
list_scene()

# ── Example: export first volume ──
volumes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
if volumes:
    out_path = os.path.join(output_dir, "exported_volume.nrrd")
    export_volume(volumes[0], out_path)

# ── Write result ──
result_file = os.environ.get("SLICER_RESULT_FILE")
if result_file:
    import json
    with open(result_file, "w") as f:
        counts = { "volumes": len(volumes) }
        f.write(json.dumps(counts))

print("[data_io] Done.")

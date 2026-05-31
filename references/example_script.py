# Example Slicer Python script — demonstrates best practices for the slicer-console skill.
#
# When writing scripts for execution via run_slicer_script.py:
#   - Use absolute paths for any input/output files.
#   - Print key results with: print("RESULT:", value)
#   - If a Slicer API method raises AttributeError, fall back to slicer.modules.*.logic().

import slicer
import vtk

# Get the scene and list all volume nodes
volumeNodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
print("Number of volumes in scene:", len(volumeNodes))

for vol in volumeNodes:
    name = vol.GetName()
    dims = vol.GetImageData().GetDimensions() if vol.GetImageData() else (0, 0, 0)
    print(f"  Volume '{name}': dimensions = {dims}")

# If no volumes exist, create a small sample volume for demonstration
if not volumeNodes:
    print("No volumes found. Creating a sample volume...")
    nodeName = "SampleVolume"
    imageSize = [64, 64, 64]
    voxelType = vtk.VTK_UNSIGNED_CHAR
    imageOrigin = [0.0, 0.0, 0.0]
    imageSpacing = [1.0, 1.0, 1.0]
    imageDirections = [1, 0, 0, 0, 1, 0, 0, 0, 1]
    fillVoxelValue = 100

    volumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", nodeName)
    imageData = vtk.vtkImageData()
    imageData.SetDimensions(imageSize)
    imageData.AllocateScalars(voxelType, 1)
    import numpy as np
    voxels = slicer.util.arrayFromVolume(volumeNode)
    voxels[:] = fillVoxelValue
    slicer.util.arrayFromVolumeModified(volumeNode)

    ijkToRas = vtk.vtkMatrix4x4()
    slicer.util.vtkMatrixFromArray(np.diag(list(imageSpacing) + [1]), ijkToRas)
    for i in range(3):
        ijkToRas.SetElement(i, 3, imageOrigin[i])
    volumeNode.SetIJKToRASMatrix(ijkToRas)

    dims = volumeNode.GetImageData().GetDimensions()
    print("Created sample volume with dimensions:", dims)

# Print a parseable result line
print("RESULT: done")

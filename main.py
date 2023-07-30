from converter_utils.ifc2usd_manager import Ifc2UsdManager
from converter_utils.args_manager import ArgsManager
from converter_utils.timer import Timer
import os
import traceback

# ---------------- ARGS MANAGEMENT ------------------- #

args_manager = ArgsManager()
input_ifc_files, output_usd_file, angular_tolerance, deflection_tolerance, generate_uvs, generate_colliders, reuse_geometry = args_manager.manage_arguments()

# ---------------- CONVERSION ------------------- #

ifc2usd_manager = Ifc2UsdManager(output_usd_file, generate_uvs, generate_colliders, reuse_geometry)

conversion_timer = Timer("Conversion")
conversion_timer.start()

for filepath in input_ifc_files:
    try:
        filename = os.path.basename(filepath)
        file_conversion_timer = Timer(f"{filename} Conversion")
        file_conversion_timer.start()

        ifc2usd_manager.convert_ifc_to_usd(filepath,
                                           angular_tolerance,
                                           deflection_tolerance)

        file_conversion_timer.stop()
    except Exception as error:
        print(f"Error -> {error}  --> input ifc file: {filepath}")
        traceback.print_exc()

conversion_timer.stop()
print(f"Conversion done! output path: {output_usd_file}")

import argparse
import os

class ArgsManager(object):
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ArgsManager, cls).__new__(cls)
        return cls.instance

    def manage_arguments(self):
        parser = argparse.ArgumentParser(
            description='Ifc2Usd helper - Example usage: \r ifc2usd -f ["C:\path-to-ifc-file.ifc"] -o "/path/to/output.usd" ',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        

        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("-f",
                            "--files",
                            action="store",
                            help="""a list of file paths.
                            --files ['file1.ifc','file2.ifc']
                            if this parameter is used, the '--folder' parameter must be omitted.""")
        
        group.add_argument("-fo",
                            "--folder",
                            action="store",
                            help="""a folder path containing all the ifc files,
                            if this parameter is used, the '--files' parameter must be omitted.""")

        parser.add_argument("-o",
                            "--output_file",
                            action="store",
                            help="""a valid path.
                            -o /path/to/output.usd""",
                            required=True)

        parser.add_argument("--angular_tolerance",
                            action="store",
                            help="angular tolerance float value.",
                            default="1.5",
                            required=False)

        parser.add_argument("--deflection_tolerance",
                            action="store",
                            help="angular tolerance float value.",
                            default="0.1",
                            required=False)

        parser.add_argument('--uvs',
                            action='store_true',
                            help="generate uvs in usd geometry mesh (except for IfcSpaces and IfcOpenings)",
                            default=False,
                            required=False
                            )
        
        parser.add_argument("--texture",
                            action='store_true',
                            help="EXPERIMENTAL, try to read and use texture ",
                            default=False,
                            required=False
                            )
        
        parser.add_argument("--ignore_ifc_type",
                            action='store',
                            help="Don't include specific ifc types",
                            default=[],
                            required=False
                            )

        parser.add_argument('--colliders',
                            action='store_true',
                            help="generate colliders in usd geometry mesh",
                            default=False,
                            required=False
                            )
        
        parser.add_argument('--reuse_mesh_ref',
                            action='store_true',
                            help=
                            """
                            use usd references to reuse meshes with same geometry
                            !!should be validated by an expert in USD!!
                            is the reusing of meshes working as expected?
                            The doubt comes from file size, shouldn't be significantly smaller where reusing lots of meshes?
                            in a test made with GLTF format, reusing the mesh buffer multiple times, decrease the size by a lot!
                            """,
                            default=False,
                            required=False
                            )

        args = parser.parse_args()

        config = vars(args)


        angular_tolerance = float(config["angular_tolerance"])  # 2  # 1.5
        deflection_tolerance = float(config["deflection_tolerance"])  # 0.14

        output_usd_file = str(config["output_file"])

        # get input ifc files, from folder parameter or from files parameter
        input_ifc_files = []
        folder = config["folder"]
        if (folder is not None):
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith('.ifc'):
                        input_ifc_files.append(folder + "/" + file)
        
        # get input ifc files array 
        if input_ifc_files is None or len(input_ifc_files) == 0:
            input_ifc_files = config["files"].replace("[", "").replace("]", "").split(",")
            input_ifc_files = [file.strip() for file in input_ifc_files]

       

        ignore_ifc_types = config["ignore_ifc_type"]

        if (len(ignore_ifc_types) > 0):
            ignore_ifc_types = ignore_ifc_types.replace("[", "").replace("]", "").split(",")
            ignore_ifc_types = [file.strip() for file in ignore_ifc_types]


        uvs = bool(config["uvs"])
        texture = bool(config["texture"])
        colliders = bool(config["colliders"])
        reuse_geometry = bool(config["reuse_mesh_ref"])

        

        return (
            input_ifc_files,
            output_usd_file,
            ignore_ifc_types,
            angular_tolerance,
            deflection_tolerance,
            uvs,
            texture,
            colliders,
            reuse_geometry)

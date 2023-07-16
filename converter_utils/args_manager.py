import argparse

class ArgsManager(object):
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(ArgsManager, cls).__new__(cls)
        return cls.instance
  

    def manage_arguments(self):
        parser = argparse.ArgumentParser(description="Ifc2Usd helper",
                                        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        parser.add_argument("-f",
                            "--files",
                            action="store",
                            help="a list of file paths. example  ->   ifc2usd.exe --files ['file1.ifc','file2.ifc']",
                            required=True)

        parser.add_argument("-o",
                            "--output_file",
                            action="store",
                            help="a valid path. example  ->   ifc2usd.exe --files ['file1.ifc','file2.ifc'] -o /path/to/output.usd",
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

        args = parser.parse_args()

        config = vars(args)

        output_usd_file = str(config["output_file"])
        input_ifc_files = config["files"].replace("[", "").replace("]", "").split(",")

        angular_tolerance = 2  # 1.5
        deflection_tolerance = 0.14

        return (input_ifc_files, output_usd_file, angular_tolerance, deflection_tolerance)
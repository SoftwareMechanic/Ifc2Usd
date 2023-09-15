# IFC Imports
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util
import ifcopenshell.util.element

import multiprocessing
import os

from converter_utils.quantity_sets_class import QuantitySet, QuantityProperty, QuantitySets
from converter_utils.property_sets_class import Property

class IfcManager():
    def __init__(self, ifc_file_path, angular_tolerance, deflection_tolerance):
        # pass
        self.ifc_file_path = ifc_file_path
        self.ifc_file = self.open_ifc_file(ifc_file_path)
        self.ifc_file_name = os.path.basename(ifc_file_path)
        self.ifc_project = None

        self.geometry_settings = self.set_ifc_geometry_settings(
            angular_tolerance,
            deflection_tolerance
        )

        self.geometry_iterator = self.set_ifc_geometry_iterator(
            self.geometry_settings,
            self.ifc_file
        )

        self.geometry_guids_iterated = dict()

        print("openshell v: " + ifcopenshell.version)

    def get_ifc_projects(self):
        return self.ifc_file.by_type('IfcProject')

    def get_ifc_project_units_assignments(self, ifc_project):
        return ifc_project.UnitsInContext.Units

    def get_ifc_project_unit_type_assignment(self, unit_type):
        """
        Given a IfcUnit returns just the unit used by the IfcProject
        """
        for unit in self.ifc_project.UnitsInContext.Units:
            # print(unit.UnitType)
            try:
                if unit.UnitType == unit_type: #LENGTHUNIT, MASSUNIT etc...
                    return unit
            except:
                pass

    def open_ifc_file(self, path):
        return ifcopenshell.open(path)

    def set_ifc_geometry_settings(self, angular_tolerance, deflection_tolerance):
        """
        Prepare the settings for the geometry iteration process.
        """
        settings = ifcopenshell.geom.settings()
        settings.set_angular_tolerance(angular_tolerance)
        settings.set_deflection_tolerance(deflection_tolerance)
        settings.force_space_transparency(1)
        settings.precision = 3
        settings.set(settings.USE_WORLD_COORDS, False)
        settings.set(settings.APPLY_DEFAULT_MATERIALS, True)
        # If true don't get normals
        settings.set(settings.WELD_VERTICES, False)
        settings.set(settings.SEW_SHELLS, True)
        settings.set(settings.CONVERT_BACK_UNITS, False)
        settings.set(settings.DISABLE_OPENING_SUBTRACTIONS, False)
        settings.set(settings.DISABLE_BOOLEAN_RESULT, False)
        # if include curves, in some case I get the same instance in the iterator
        # more than once, with different geometry, # workaround is to take the
        # shapes with more vertices, if I exclude, I get colors issue in some cases
        settings.set(settings.INCLUDE_CURVES, True)
        settings.set(settings.EXCLUDE_SOLIDS_AND_SURFACES, False)
        # if APPLY_LAYERSETS is false and LAYERSET_FIRST is true, it happened that I can not retrieve the texture, Instead I can get them if set to opposites,
        # but with a model I tried the texture of a wall also occupy the space of openings (door, window).
        # TODO: test with other IFC files with textures and TODO maybe manage a new argument for this program in order to let the used decide
        settings.set(settings.APPLY_LAYERSETS, True) 
        settings.set(settings.LAYERSET_FIRST, False)
        settings.set(settings.NO_NORMALS, False)
        settings.set(settings.GENERATE_UVS, True)
        settings.set(settings.EDGE_ARROWS, False)
        settings.set(settings.SITE_LOCAL_PLACEMENT, True)
        settings.set(settings.BUILDING_LOCAL_PLACEMENT, True)
        settings.set(settings.BOOLEAN_ATTEMPT_2D, True)
        settings.set(settings.VALIDATE_QUANTITIES, True)
        settings.set(settings.NO_WIRE_INTERSECTION_CHECK, False)
        settings.set(settings.NO_WIRE_INTERSECTION_TOLERANCE, False)
        settings.set(settings.STRICT_TOLERANCE, True)
        settings.set(settings.DEBUG_BOOLEAN, False)

        return settings

    def set_ifc_geometry_iterator(self, settings, ifc_file):
        """
        Prepare the geometry iterator for the relative IFC file with relative settings.
        """
        iterator = ifcopenshell.geom.iterator(
            settings,
            ifc_file,
            multiprocessing.cpu_count()
        )
        return iterator

    def get_ifc_mesh_info(self, ifc_geometry_iterator):
        """
        Get the necessary mesh information as follows:\n
        guid, ifc_type, faces, verts, matrix, materials, materials_ids, uvs
        """
        # Get ifc object
        shape = self.geometry_iterator.get()
        # Get GUID of ifc object
        guid = shape.guid

        faces = shape.geometry.faces

        if len(faces) == 0:
            #some times it happens that mesh are calculated more than once and have no faces
            return

        verts = shape.geometry.verts

        if (self.geometry_guids_iterated.get(guid) != None):  
            print("Found duplicate guid in geometry iterator, probably with different geometry data")
            if len(verts) > len(self.geometry_guids_iterated[guid]):
                self.geometry_guids_iterated[guid] = verts
            else:
                return

        self.geometry_guids_iterated[guid] = verts

        matrix = list(shape.transformation.matrix.data)

        #Surface styles (not ever connected to Ifc Materials)
        materials = shape.geometry.materials
        materials_ids = shape.geometry.material_ids


        uvs = shape.geometry.uvs()
        
        ifc_type = shape.product.is_a()

        return (guid, ifc_type, faces, verts, matrix, materials, materials_ids, uvs)

    def get_element_properties(self, ifc_property_set):
        """
        return the element properties of the given property set.
        """
        element_properties = []
       
        if hasattr(ifc_property_set, 'HasProperties') is False:
            return None
        for prop in ifc_property_set.HasProperties:
            # TODO: manage in the pset class also the type of the property?
            # this could help in improve UI relative to property in externals softwares
            
            if prop.is_a('IfcPropertySingleValue'):
                # Also here we need to check the property type of the value it could be electric value or length value
                
                nominal_value_info = prop.NominalValue.get_info() if prop.NominalValue is not None else dict()
                wrapped_value = str(nominal_value_info.get("wrappedValue"))  or ""
                value_type = nominal_value_info.get("type") or ""
                value_unit = ""

                if value_type.endswith('Measure'):
                    value_unit =  self.from_measure_to_unit(value_type)

                #element_properties[prop.Name] = wrapped_value
                property = Property(prop.Name, value_type, value_unit, wrapped_value  )
                element_properties.append(property)

            elif prop.is_a('IfcPropertyEnumeratedValue'):
                enumerated_prop_info = prop.get_info()
                enumeration_name = enumerated_prop_info["Name"]
                value_type = enumerated_prop_info["type"]

                values = ""
                for value in enumerated_prop_info["EnumerationValues"]:
                    prop_value = value.get_info().get("wrappedValue", "")
                    values += f"{prop_value}, "

                values = values.removesuffix(", ")
                #element_properties[prop.Name] = values

                property = Property(prop.Name, value_type, "", values)
                element_properties.append(property)


            elif prop.is_a('IfcPropertyBoundedValue'):
                bounded_property_info = prop.get_info()

                lower_bound_value = bounded_property_info["LowerBoundValue"]
                upper_bound_value = bounded_property_info["UpperBoundValue"]
                value_type = ""
                unit = ""

                if lower_bound_value is None:
                    lower_bound_value = "NOT DEFINED"
                else:
                    value_info = lower_bound_value.get_info()
                    wrapped_value = str(value_info["wrappedValue"])
                    value_type = str(value_info["type"])
                    unit = self.from_measure_to_unit(value_type)

                   
                    upper_bound_value = str(wrapped_value)
                if upper_bound_value is None:
                    upper_bound_value = "NOT DEFINED"
                else:
                    value_info = upper_bound_value.get_info()
                    wrapped_value = str(value_info["wrappedValue"])
                    value_type = str(value_info["type"])
                    unit = self.from_measure_to_unit(value_type)

                    upper_bound_value = str(wrapped_value)

                prop_value = f"{lower_bound_value} , {upper_bound_value}"
                # element_properties[prop.Name] = prop_value

                property = Property(prop.Name, value_type, "", prop_value)
                element_properties.append(property)

            elif prop.is_a("IfcPropertyListValue"):
                values = ""
                value_type = ""
                unit = ""
                for value in prop.ListValues:
                    prop_value_info = value.get_info()
                    wrapped_value = str(prop_value_info.get("wrappedValue", ""))
                    value_type = prop_value_info.get("type") or ""
                    unit = self.from_measure_to_unit(value_type)

                    values += f"{wrapped_value}, "

                values = values.removesuffix(", ")
                #element_properties[prop.Name] = values
                property = Property(prop.Name, value_type, "", values)
                element_properties.append(property)
            else:
                print("Unknown property type -> ", prop.is_a())
        
        return element_properties

    def get_element_quantities(self, quantity_set):
        """
        return the element properties of the given quantity set.
        """
        quantity_set_instance = QuantitySet(quantity_set.Name)
        
        for quantity in quantity_set.Quantities:
            
            if quantity.is_a('IfcQuantityLength'):
                unit = self.get_ifc_project_unit_type_assignment("LENGTHUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)

                quantity_property = QuantityProperty(quantity.Name, "IfcQuantityLength", symbol, str(quantity.LengthValue))
                quantity_set_instance.Properties.append(quantity_property)
            elif quantity.is_a('IfcQuantityArea'):
                unit = self.get_ifc_project_unit_type_assignment("AREAUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
                quantity_property = QuantityProperty(quantity.Name, "IfcQuantityArea", symbol, str(quantity.AreaValue))
                quantity_set_instance.Properties.append(quantity_property)
            elif quantity.is_a('IfcQuantityVolume'):
                unit = self.get_ifc_project_unit_type_assignment("VOLUMEUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
                quantity_property = QuantityProperty(quantity.Name, "IfcQuantityVolume", symbol, str(quantity.VolumeValue))
                quantity_set_instance.Properties.append(quantity_property)
            elif quantity.is_a('IfcQuantityCount'):
                quantity_property = QuantityProperty(quantity.Name, "IfcQuantityCount", "", str(quantity.CountValue))
                quantity_set_instance.Properties.append(quantity_property)
            elif quantity.is_a('IfcQuantityWeight'):
                unit = self.get_ifc_project_unit_type_assignment("MASSUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
                # element_quantities[quantity.Name] = str(quantity.WeightValue) + " " + symbol
                quantity_property = QuantityProperty(quantity.Name, "IfcQuantityWeight", symbol, str(quantity.WeightValue))
                quantity_set_instance.Properties.append(quantity_property)

            else:
                print("Unknown quantity type")
                print(quantity.is_a())
                # for attr in dir(quantity):
                #     print(getattr(quantity, ", ", attr))
                # print(dir(quantity))
                # element_quantities[quantity.Name] = ""
                # print(quantity.Name)

            #add quant ity suffix symbol
            # element_quantities[quantity.Name] += ' ' + self.get_unit_prefix_symbol(quantity)  + self.get_unit_name_symbol(quantity)
        
        # Here I could return just quantity_set.Quantities instead of cycle them, but Unit is null everytime
        return quantity_set_instance

    def get_element_type(self, type):
        element_name = dict()
        element_name["name"] = type.Name
        return element_name

    def get_element_ifc_type(self, ifc_element):
        element_type = dict()
        element_type["type"] = ifc_element.is_a()
        return element_type

    def get_unit_prefix_symbol(self, quantity):
        """
        given a quantity returns the unit prefix in short way (e.g. if the quantity prefix is KILO returns k).
        """
        unit_prefix = None if hasattr(quantity, "Prefix") is False else quantity.Prefix
        match unit_prefix:
            case "EXA":
                return "E"
            case "PETA":
                return "P"
            case "TERA":
                return "T"
            case "GIGA":
                return "G"
            case "MEGA":
                return "M"
            case "KILO":
                return "k"
            case "HECTO":
                return "h"
            case "DECA":
                return "da"
            case "":
                return ""
            case "DECI":
                return "d"
            case "CENTI":
                return "c"
            case "MILLI":
                return "m"
            case "MICRO":
                return "mc"
            case "NANO":
                return "n"
            case "PICO":
                return "p"
            case "FEMTO":
                return "f"
            case "ATTO":
                return "a"
            case _:
                return ""

    def get_unit_name_symbol(self, quantity):
        """
        given a quantity returns the unit name in short way (e.g. if the quantity prefix is METRE returns m).
        """
        unit_name = None if hasattr(quantity, "Name") is False else quantity.Name 
        if unit_name is None:
            return ""
        match unit_name:
            case "METRE":
                return "m"
            case "SQUARE_METRE":
                return "m2"
            case "CUBIC_METRE":
                return "m3"
            case "SECOND":
                return "s"
            case "HERTZ":
                return "z"
            case "DEGREE_CELSIUS":
                return "C°"
            case "AMPERE":
                return "A"
            case "VOLT":
                return "V"
            case "WATT":
                return "W"
            case "NEWTON":
                return "N"
            case "LUX":
                return "lx"
            case "LUMEN":
                return "lm"
            case "CANDELA":
                return "cd"
            case "PASCAL":
                return "Pa"
            case "DEGREE":
                return "°"
            case _:
                print("Unmanaged symbol for unit name: ", unit_name)
                return ""

    def from_measure_to_unit(self, measure_type):
        """
        given an IFC measure type return the relative symbol/unit (e.g. if the measure is 'IfcPowerMeasure' based on IfcProject this could return KW (kilowatt)).
        """
        unit = ""
        symbol = ""
        match measure_type:
            # Electrical measures
            case "IfcElectricCurrentMeasure":
                unit = self.get_ifc_project_unit_type_assignment("ELECTRICCURRENTUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
            case "IfcElectricResistanceMeasure":
                unit = self.get_ifc_project_unit_type_assignment("ELECTRICRESISTANCEUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
            case "IfcElectricVoltageMeasure":
                unit = self.get_ifc_project_unit_type_assignment("ELECTRICVOLTAGEUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
            case "IfcPowerMeasure":
                unit = self.get_ifc_project_unit_type_assignment("POWERUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)

             # Space measures
            case "IfcVolumeMeasure":
                unit = self.get_ifc_project_unit_type_assignment("VOLUMEUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
            case "IfcLengthMeasure":
                unit = self.get_ifc_project_unit_type_assignment("LENGHTUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
            case "IfcAreaMeasure":
                unit = self.get_ifc_project_unit_type_assignment("AREAUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)

            case "IfcPlaneAngleMeasure":
                unit = self.get_ifc_project_unit_type_assignment("PLANEANGLEUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
            case "IfcThermodynamicTemperatureMeasure":
                unit = self.get_ifc_project_unit_type_assignment("THERMODYNAMICTEMPERATUREUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
            case "IfcThermalTransmittanceMeasure":
                unit = self.get_ifc_project_unit_type_assignment("THERMALTRANSMITTANCEUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
            case "IfcVolumetricFlowRateMeasure":
                unit = self.get_ifc_project_unit_type_assignment("VOLUMETRICFLOWRATEUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
            case _:
                print("Unmanaged measure: ", measure_type)

        return symbol
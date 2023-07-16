# IFC Imports
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util
import ifcopenshell.util.element

import multiprocessing

from pxr import Usd, UsdGeom, Vt, Gf, Sdf, UsdShade

class IfcManager():
    def __init__(self, ifc_file_path, angular_tolerance, deflection_tolerance):
        # pass
        self.ifc_file = self.open_ifc_file(ifc_file_path)
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

        #self.project_units = self.get_ifc_projects()[0].UnitsInContext.Units

    def get_ifc_projects(self):
        return self.ifc_file.by_type('IfcProject')
    
    def get_ifc_project_units_assignments(self, ifc_project):
        return ifc_project.UnitsInContext.Units
    
    def get_ifc_project_unit_type_assignment(self, unit_type):
        for unit in self.ifc_project.UnitsInContext.Units:
            # print(unit.UnitType)
            if unit.UnitType == unit_type: #LENGTHUNIT, MASSUNIT etc...
                return unit

    def open_ifc_file(self, path):
        return ifcopenshell.open(path)

    def set_ifc_geometry_settings(self, angular_tolerance, deflection_tolerance):
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
        settings.set(settings.APPLY_LAYERSETS, True)
        settings.set(settings.LAYERSET_FIRST, False)
        settings.set(settings.NO_NORMALS, True)
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
        

    def set_ifc_geometry_iterator(self,settings, ifc_file):
        iterator = ifcopenshell.geom.iterator(
            settings,
            ifc_file,
            multiprocessing.cpu_count()
        )
        return iterator
    

    def get_ifc_mesh_info(self, ifc_geometry_iterator):
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

        ifc_type = shape.product.is_a()

        return (guid, ifc_type, faces, verts, matrix, materials, materials_ids)


    # PropertySet
    def get_element_properties(self,ifc_property_set, prim, namespace):
        element_properties = dict()
        for prop in ifc_property_set.HasProperties:
            if prop.is_a('IfcPropertySingleValue'):
                element_properties[prop.Name] =  str(prop.NominalValue) # if prop.NominalValue is None else str(prop.NominalValue.wrappeValue)

            else:
                print("Not an IfcPropertySingleValue, ", prop.is_a())
                #for prop in dir(ifc_property_set):
                    #print(prop, " ", getattr(ifc_property_set, prop))
                

        return element_properties


    def get_element_quantities(self,quantity_set, prim, namespace):
        element_quantities = dict()
        for quantity in quantity_set.Quantities:
            if quantity.is_a('IfcQuantityLength'):
                unit = self.get_ifc_project_unit_type_assignment("LENGTHUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
                element_quantities[quantity.Name] = str(quantity.LengthValue) + " " + symbol
            elif quantity.is_a('IfcQuantityArea'):
                unit = self.get_ifc_project_unit_type_assignment("AREAUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
                element_quantities[quantity.Name] = str(quantity.AreaValue) + " " + symbol
            elif quantity.is_a('IfcQuantityVolume'):
                unit = self.get_ifc_project_unit_type_assignment("VOLUMEUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
                element_quantities[quantity.Name] = str(quantity.VolumeValue) + " " + symbol
            elif quantity.is_a('IfcQuantityCount'):
                # unit = self.get_ifc_project_unit_type_assignment("VOLUMEUNIT")
                # symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
                element_quantities[quantity.Name] = str(quantity.CountValue) # + " " + symbol
            elif quantity.is_a('IfcQuantityWeight'):
                unit = self.get_ifc_project_unit_type_assignment("MASSUNIT")
                symbol = self.get_unit_prefix_symbol(unit) + self.get_unit_name_symbol(unit)
                element_quantities[quantity.Name] = str(quantity.WeightValue) + " " + symbol

                print("Part of complex, ", quantity.PartOfComplex)
                print("unit -> ", quantity.Unit)

            else:
                print("Unknown quantity type")
                print(quantity.is_a())
                for attr in dir(quantity):
                    print(getattr(quantity, ", ", attr))
                print(dir(quantity))
                element_quantities[quantity.Name] = ""
                # print(quantity.Name)

            #add quantity suffix symbol
            element_quantities[quantity.Name] += ' ' + self.get_unit_prefix_symbol(quantity)  + self.get_unit_name_symbol(quantity)

        return element_quantities
        

    def get_element_type(self,type, usd_prim):
        element_name = dict()
        element_name["name"] = type.Name
        
        return element_name


    def get_element_ifc_type(self, ifc_element):
        element_type = dict()
        element_type["type"] = ifc_element.is_a()
        return element_type
    

    def get_unit_prefix_symbol(self, quantity):
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
        unit_name = None if hasattr(quantity, "Name") is False else quantity.Name 
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
                return ""

    
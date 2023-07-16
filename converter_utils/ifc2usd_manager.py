from converter_utils.ifc_manager import IfcManager
from converter_utils.usd_manager import UsdManager

import os

from converter_utils.property_sets_class import PropertySet, PropertySets



class Ifc2UsdManager():
    def __init__(self, usd_output_path):
        self.ifc_manager = None
        self.usd_manager = UsdManager(usd_output_path)

        self.ifc_types_and_counters = dict()

        self.usd_namespace_delimiter = ":"
        self.base_namespace = "IFC"
        self.property_sets_namespace = f"{self.base_namespace}{self.usd_namespace_delimiter}property_sets"
        self.quantity_sets_namespace = f"{self.base_namespace}{self.usd_namespace_delimiter}quantity_sets"


    def convert_ifc_to_usd(self, ifc_file_path, angular_tolerance, deflection_tolerance):

        self.usd_manager.clear_prims_reference()
        self.ifc_manager = IfcManager(ifc_file_path, angular_tolerance, deflection_tolerance )

        
        filename_without_extension = os.path.basename(ifc_file_path).split('.')[0]
        # ifc_file = self.ifc_manager.open_ifc_file(ifc_file_path)
        # geometry_settings = self.ifc_manager.set_ifc_geometry_settings(
        #     angular_tolerance,
        #     deflection_tolerance
        # )

        # geometry_iterator = self.ifc_manager.set_ifc_geometry_iterator(
        #     geometry_settings,
        #     ifc_file
        # )

        
        model_prim = self.usd_manager.define_container_prim(
            filename_without_extension
        )

        

        ifc_geometry_iterator = self.ifc_manager.geometry_iterator

        self.create_ifc_hierarchy_in_usd(model_prim, self.usd_manager.stage)

        # ifc_projects = self.ifc_manager.get_ifc_projects()
        # for ifc_project in ifc_projects:
        #     self.create_ifc_hierarchy_in_usd(
        #         ifc_project,
        #         model_prim,
        #         self.usd_manager.stage
        #     )

        if ifc_geometry_iterator.initialize():
            try:
                while True:
                    #usd_manager.create_usd_mesh(geometry_iterator)

                    

                    ifc_mesh_info = self.ifc_manager.get_ifc_mesh_info(ifc_geometry_iterator)

                    if (ifc_mesh_info is None):
                        if not ifc_geometry_iterator.next():
                            break
                        continue

               
                    guid, ifc_type, faces, verts, matrix, materials, materials_ids = ifc_mesh_info

                    matrix = self.fix_matrix(matrix)

                    #Test pymesh
                    
                    #end test

                    usd_mesh = self.usd_manager.create_usd_mesh_(guid, faces, verts, matrix)

                    self.manage_mesh_material(ifc_type, materials, materials_ids, usd_mesh)
                    
                    if not ifc_geometry_iterator.next():
                        break
            except Exception as e:
                print(e)


        self.usd_manager.save_stage()

    def manage_mesh_material(self, ifc_type, materials, materials_ids, usd_mesh):
        if ifc_type == "IfcOpeningElement" or ifc_type == "IfcSpace":
            self.usd_manager.assign_mesh_material(usd_mesh, "transparent", [0.0, 0.0, 0.0], 0.0)
                    
        else:
            if len(materials) == 1:
                material = materials[0]
                material_name = material.name
                material_color = material.diffuse
                material_transparency = 1.0

                if material.has_transparency:
                    material_transparency = 1 - material.transparency

                self.usd_manager.assign_mesh_material(usd_mesh, material_name, material_color, material_transparency)

            else:
                materials_ids_and_counts = self.get_materials_ids_and_relative_counts(materials_ids)

                material_start_index_faces_indices = 0
                for material_id_and_count in materials_ids_and_counts:
                    material_id = material_id_and_count[0]
                    material_count = material_id_and_count[1]
                    material = materials[material_id]
                    material_transparency = 1.0

                    if material.has_transparency:
                        material_transparency = 1 - material.transparency

                    self.usd_manager.assign_mesh_subset_material(usd_mesh, material.name, material.diffuse, material_transparency, material_start_index_faces_indices, material_count )

                    material_start_index_faces_indices += material_count


    def create_ifc_hierarchy_in_usd(self, model_prim, usd_stage):
        ifc_projects = self.ifc_manager.get_ifc_projects()
        for ifc_project in ifc_projects:
            self.ifc_manager.ifc_project = ifc_project
            self._create_ifc_hierarchy_in_usd(
                ifc_project,
                model_prim,
                usd_stage
            )
        
        print("hierarchy created")


    def _create_ifc_hierarchy_in_usd(self, ifc_element, parent_prim, stage):
        # print('#' + str(ifc_element.id()) + ' = ' + ifc_element.is_a() + ' "' + str(ifc_element.Name) + '" (' + ifc_element.GlobalId + ')' )
        # prim = stage.DefinePrim(str(parent_prim.GetPath()) + self.usd_manager.get_safe_prim_name(ifc_element.GlobalId))

        # define common variables
        guid = ifc_element.GlobalId
        element_type = ifc_element.is_a()

        # define the name to use for the element
        ifc_type_counter = self.ifc_types_and_counters.get(element_type)
        if ifc_type_counter is None:
            self.ifc_types_and_counters[element_type] = 0
        else:
            self.ifc_types_and_counters[element_type] = ifc_type_counter + 1

        prim_name = element_type + "_" + str(self.ifc_types_and_counters[element_type])

        # group by ifc types  TODO: use a flag to indicate if group or not? maybe default = true?

        is_type_container_created = self.usd_manager.is_prim_already_created(parent_prim, element_type)
        if is_type_container_created is False:
            parent_prim = self.usd_manager.create_prim(parent_prim, guid, element_type, "Scope")
        else:
            parent_prim = self.usd_manager.get_prim_if_created(parent_prim, element_type)

        
        prim = self.usd_manager.create_prim(parent_prim, guid, prim_name)
        self.usd_manager.create_prim_string_attribute(prim, "guid", guid, self.base_namespace)
        self.usd_manager.create_prim_string_attribute(prim, "ifcType", element_type, self.base_namespace)


        property_sets_instance = PropertySets()
        quantity_sets_instance = PropertySets()

        
        #--------------------MANAGE PROPERTIES -----------------------#
        for definition in ifc_element.IsDefinedBy:
            if definition.is_a('IfcRelDefinesByProperties'):
                related_data = definition.RelatingPropertyDefinition
                #the individual properties/quantities
                if related_data.is_a('IfcPropertySet'):
                    property_set_name = related_data.Name
                    properties = self.ifc_manager.get_element_properties(
                        related_data,
                        prim,
                        self.property_sets_namespace
                    )

                    if len(properties) == 0:
                        continue

                    property_set = PropertySet(property_set_name)
                    property_set.properties = properties
                    property_sets_instance.property_sets.append(property_set)

                    # namespace = f"{self.property_sets_namespace}:{property_set_name}"


                    # for property_key in properties.keys():
                    #     self.usd_manager.create_prim_string_attribute(prim, property_key, properties[property_key], namespace )

                elif related_data.is_a('IfcElementQuantity'):
                    quantity_set_name = related_data.Name
                    quantities = self.ifc_manager.get_element_quantities(
                        related_data,
                        prim,
                        self.quantity_sets_namespace
                    )

                    property_set = PropertySet(quantity_set_name)
                    property_set.properties = quantities
                    quantity_sets_instance.property_sets.append(property_set)


                    # namespace = f"{self.quantity_sets_namespace}:{quantity_set_name}"


                    # for property_key in quantities.keys():
                    #     self.usd_manager.create_prim_string_attribute(prim, property_key, quantities[property_key], namespace )


            if definition.is_a('IfcRelDefinesByType'):
                name = self.ifc_manager.get_element_type(
                    definition.RelatingType,
                    prim
                )

                namespace = f"{self.base_namespace}:name"

                for name_key in name.keys():
                    self.usd_manager.create_prim_string_attribute(prim, name_key, name[name_key], namespace )

            if definition.is_a('IfcRelDefinesByTemplate'):
                print("IfcRelDefinesByTemplate")
               

            if definition.is_a('IfcRelDefinesByObject'):
                print("IfcRelDefinesByObject")

        
        
        #Setting all the psets as a prim attribute 
        #if we use namespaces to define also the single property set level
        #may cause errors because of characters not authorized in namespaces/key for attributes
        #but all chars are ok in the value field of the attribute

        self.usd_manager.create_prim_string_attribute(prim, "propertySets", property_sets_instance.toJSON(), self.base_namespace )
        self.usd_manager.create_prim_string_attribute(prim, "quantitySets", quantity_sets_instance.toJSON(), self.base_namespace )

        #-----------------------HIERARCHY CONSTRUCTION -----------------------
        # follow Spatial relation
        if (ifc_element.is_a('IfcSpatialStructureElement')):
            for rel in ifc_element.ContainsElements:
                relatedElements = rel.RelatedElements
                for child in relatedElements:
                    self._create_ifc_hierarchy_in_usd(child,  prim, stage)        
        # follow Aggregation Relation
        if (ifc_element.is_a('IfcObjectDefinition')):
            # print(ifc_element.is_a(), " IfcObjectDefinition:")
            for rel in ifc_element.IsDecomposedBy:
                relatedObjects = rel.RelatedObjects
                for child in relatedObjects:
                    self._create_ifc_hierarchy_in_usd(child,  prim, stage)
        # check for openings
        if (ifc_element.is_a('IfcElement')):
            if len(ifc_element.HasOpenings) > 0:
                for openingRelation in ifc_element.HasOpenings:
                    opening = openingRelation.RelatedOpeningElement
                    self._create_ifc_hierarchy_in_usd(opening,  parent_prim.GetParent(), stage)

    

    def get_materials_ids_and_relative_counts(self, materials_ids):
        vectorWithMatIdsAndRelativeIndicesCount = []
        lastMaterialId = -1
        indicesSizeFoundWithLastMaterialId = 0

        m_i = 0

        while m_i < len(materials_ids):
            materialId = materials_ids[m_i]
            #print(materialId)

            # if is the first iteration, last material ID is material is actual material ID  
            if (m_i == 0):
                lastMaterialId = materialId
            
            # if material ID is equals to last material ID, the count for this ID is increased by 1
            if (materialId == lastMaterialId):
                indicesSizeFoundWithLastMaterialId += 1

            # if material ID is different then last material ID |OR| material ID INDEX the last of the list
            # add the id with the relative indices count
            if (materialId != lastMaterialId or m_i == len(materials_ids) - 1):
                vectorWithMatIdsAndRelativeIndicesCount.append((lastMaterialId, indicesSizeFoundWithLastMaterialId))
                #face_colors.extend([ifc_materials[materialId].diffuse] * indicesSizeFoundWithLastMaterialId)
                        
                lastMaterialId = materialId
                indicesSizeFoundWithLastMaterialId = 1
                

            m_i += 1

        return vectorWithMatIdsAndRelativeIndicesCount
    
    
    def fix_matrix(self, matrix):
        #matrix obtained by IFC are 3x4, we need 4x4 matrix
        matrix.insert(3, 0)
        matrix.insert(7, 0)
        matrix.insert(11, 0)
        matrix.insert(15, 1)

        return matrix



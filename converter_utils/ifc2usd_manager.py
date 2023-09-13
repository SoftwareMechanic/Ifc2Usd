from converter_utils.ifc_manager import IfcManager
from converter_utils.quantity_sets_class import QuantitySets
from converter_utils.usd_manager import UsdManager

import os
import shutil

from converter_utils.property_sets_class import PropertySet, PropertySets
from converter_utils.object_type_class import ObjectInfo


class Ifc2UsdManager():
    def __init__(self, usd_output_path, generate_uvs, generate_colliders, reuse_geometry):
        self.ifc_manager = None
        self.usd_manager = UsdManager(usd_output_path)
        

        self.ifc_types_and_counters = dict()

        self.usd_namespace_delimiter = ":"
        self.base_namespace = "IFC"
        self.property_sets_namespace = f"{self.base_namespace}{self.usd_namespace_delimiter}property_sets"
        self.quantity_sets_namespace = f"{self.base_namespace}{self.usd_namespace_delimiter}quantity_sets"
        self.usd_output_path = usd_output_path
        # Dict initialized for reuse geometry
        self.verts_and_relative_usd_mesh_path = dict()

        self.generate_uvs = generate_uvs
        self.generate_colliders = generate_colliders
        self.reuse_geometry = reuse_geometry
        



    def convert_ifc_to_usd(self, ifc_file_path, angular_tolerance, deflection_tolerance):
        self.usd_manager.clear_prims_reference()
        self.ifc_manager = IfcManager(ifc_file_path, angular_tolerance, deflection_tolerance )

        filename_without_extension = os.path.basename(ifc_file_path).split('.')[0]

        model_prim = self.usd_manager.define_container_prim(
            filename_without_extension
        )

        ifc_geometry_iterator = self.ifc_manager.geometry_iterator

        self.create_ifc_hierarchy_in_usd(model_prim, self.usd_manager.stage)

        mesh_reused_counter = 0
        if ifc_geometry_iterator.initialize():
            try:
                while True:
                    ifc_mesh_info = self.ifc_manager.get_ifc_mesh_info(ifc_geometry_iterator)

                    if (ifc_mesh_info is None):
                        if not ifc_geometry_iterator.next():
                            break
                        continue

                    guid, ifc_type, faces, verts, matrix, materials, materials_ids, uvs = ifc_mesh_info

                    matrix = self.fix_matrix(matrix)

                    # TODO: just for completness, create an argument flag to determine if reuse mesh references or not?

                    if (self.reuse_geometry):
                        is_same_mesh_used = self.verts_and_relative_usd_mesh_path.get(verts) is not None
                        if (is_same_mesh_used):
                            mesh_to_reuse = self.verts_and_relative_usd_mesh_path[verts]
                            usd_mesh = self.usd_manager.reuse_usd_mesh(guid, mesh_to_reuse)
                            self.set_usd_mesh(usd_mesh, faces, verts, matrix, uvs)
                           

                            self.manage_mesh_material(ifc_type, materials, materials_ids, usd_mesh)
                            mesh_reused_counter += 1
                        else:
                            usd_mesh = self.usd_manager.create_usd_mesh_(guid)
                            self.set_usd_mesh(usd_mesh, faces, verts, matrix, uvs)

                            self.manage_mesh_material(ifc_type, materials, materials_ids, usd_mesh)

                            self.verts_and_relative_usd_mesh_path[verts] = str(usd_mesh.GetPath())
                    else:
                        usd_mesh = self.usd_manager.create_usd_mesh_(guid)
                        self.set_usd_mesh(usd_mesh, faces, verts, matrix, uvs)
                        self.manage_mesh_material(ifc_type, materials, materials_ids, usd_mesh)

                    if not ifc_geometry_iterator.next():
                        break

                print("Potential mesh to reuse ", mesh_reused_counter)
            except Exception as e:
                print(e)

        self.usd_manager.save_stage()

    def set_usd_mesh(self, usd_mesh, faces, verts, matrix, uvs):
        #usd_mesh = self.usd_manager.create_usd_mesh_(name)
        self.usd_manager.generate_mesh_vertices(usd_mesh, verts)
        self.usd_manager.generate_mesh_indices(usd_mesh, faces)
        self.usd_manager.assign_transform_matrix(usd_mesh, matrix)  # use prim instead of mesh?
        if (self.generate_colliders):
            self.usd_manager.generate_collider(usd_mesh.GetPrim())  # use prim instead of mesh?
        if (self.generate_uvs):
            self.usd_manager.generate_uvs(usd_mesh, uvs)


    def manage_mesh_material(self, ifc_type, materials, materials_ids, usd_mesh):
        if ifc_type == "IfcOpeningElement" or ifc_type == "IfcSpace":
            self.usd_manager.assign_mesh_material(usd_mesh, "transparent", [0.0, 0.0, 0.0], 0.0)
        else:
            if len(materials) == 1:
                material = materials[0]
                material_name = material.original_name()
                if (material_name == "" or material_name is None):
                    material_name = "undefined"
                material_color = material.diffuse
                material_transparency = 1.0

                #print(dir(material))

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

                    texture_name = self.get_relative_texture_if_available(material.original_name())
                    relative_texture_path = self.get_relative_texture_path(texture_name)

                    self.usd_manager.assign_mesh_subset_material(usd_mesh, material.original_name(), material.diffuse, relative_texture_path, material_transparency, material_start_index_faces_indices, material_count )

                    material_start_index_faces_indices += material_count

    def get_relative_texture_path(self, texture_name):
        relative_texture_path = None

        if texture_name is not None:
            relative_texture_path = "textures/" + texture_name 
            ifc_directory = os.path.dirname(self.ifc_manager.ifc_file_path)
            usd_output_directory = os.path.dirname(self.usd_output_path)
            texture_file_path = f"{ifc_directory}/{texture_name}"
            os.makedirs(f"{usd_output_directory}/textures", exist_ok=True)
            shutil.copy(texture_file_path, f"{usd_output_directory}/textures/{texture_name}")
        return relative_texture_path

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
        # define common variables
        ifc_element_info = ifc_element.get_info()
        
        obj_placement = ifc_element_info.get("ObjectPlacement") or None
        if obj_placement is not None:
            #print(dir(obj_placement))
            
            #print(str(obj_placement.PlacementRelTo))
            #print(obj_placement.PlacesObject)
            #print(str(obj_placement.ReferencedByPlacements))
            #print(obj_placement.RelativePlacement.get_info())
            pass

        guid = ifc_element.GlobalId
        ifc_entity = ifc_element.is_a()

        # define the name to use for the element
        ifc_type_counter = self.ifc_types_and_counters.get(ifc_entity)
        if ifc_type_counter is None:
            self.ifc_types_and_counters[ifc_entity] = 0
        else:
            self.ifc_types_and_counters[ifc_entity] = ifc_type_counter + 1

        counter_for_type = str(self.ifc_types_and_counters[ifc_entity])
        prim_name = ifc_entity + "_" + counter_for_type

        # group by ifc types  TODO: use a flag to indicate if group or not?

        is_type_container_created = self.usd_manager.is_prim_already_created(
            parent_prim,
            ifc_entity)

        if is_type_container_created is False:
            parent_prim = self.usd_manager.create_prim(
                parent_prim,
                guid,
                ifc_entity,
                "Scope")
        else:
            parent_prim = self.usd_manager.get_prim_if_created(
                parent_prim,
                ifc_entity)

        prim = self.usd_manager.create_prim(parent_prim, guid, prim_name)
        self.usd_manager.create_prim_string_attribute(
            prim,
            "guid",
            guid,
            self.base_namespace)

        self.usd_manager.create_prim_string_attribute(
            prim,
            "ifcType",
            ifc_entity,
            self.base_namespace)

        property_sets_instance = PropertySets()
        quantity_sets_instance = QuantitySets()
        object_info = ObjectInfo()

        object_info.GUID = guid
        object_info.IfcEntity = ifc_entity
        object_info.Name = ifc_element_info.get("Name") or ""
        object_info.Description = ifc_element_info.get("Description") or ""
        object_info.OverallHeight = ifc_element_info.get("OverallHeight") or ""
        object_info.OverallWidth = ifc_element_info.get("OverallWidth") or ""
        object_info.ObjectType = ifc_element_info.get("ObjectType") or ""
        object_info.ObjectType = ifc_element_info.get("Tag") or ""

        # --------------------MANAGE PROPERTIES -----------------------#
        for definition in ifc_element.IsDefinedBy:
            if definition.is_a('IfcRelDefinesByProperties'):
                related_data = definition.RelatingPropertyDefinition

                if related_data.is_a('IfcPropertySet'):
                    property_set_name = related_data.Name
                    property_set_guid = related_data.GlobalId
                    properties = self.ifc_manager.get_element_properties(
                        related_data,
                    )

                    if properties is None or len(properties) == 0:
                        continue

                    property_set = PropertySet(property_set_guid, property_set_name)
                    property_set.Properties = properties
                    property_sets_instance.property_sets.append(property_set)

                elif related_data.is_a('IfcElementQuantity'):
                    quantitySet = self.ifc_manager.get_element_quantities(
                        related_data,
                    )

                    quantity_sets_instance.quantity_sets.append(quantitySet)

            if definition.is_a('IfcRelDefinesByType'):
                definition_type_info = definition.RelatingType.get_info()

                object_info.ConstructionType = definition_type_info.get("ConstructionType") or ""
                object_info.OperationType = definition_type_info.get("OperationType") or ""
                object_info.PredefinedType = definition_type_info.get("PredefinedType") or ""
                object_info.ElementType = definition_type_info.get("ElementType") or ""

                #ifcObjectType = ObjectInfo(guid, ifc_entity, definition_type, definition_name, definition_tag, definition_element_type, definition_predefined_type, definition_construction_type, definition_operation_type)

                if (definition.RelatingType.HasPropertySets is not None):

                    for property_set in definition.RelatingType.HasPropertySets:
                        pset_name = property_set.Name
                        pset_guid = property_set.GlobalId
                        properties = self.ifc_manager.get_element_properties(
                            property_set,
                        )

                        if properties is None or len(properties) == 0:
                            continue

                        property_set_instance = PropertySet(pset_guid, pset_name)
                        property_set_instance.properties = properties
                        property_sets_instance.property_sets.append(property_set_instance)

            if definition.is_a('IfcRelDefinesByTemplate'):
                print("IfcRelDefinesByTemplate")

            if definition.is_a('IfcRelDefinesByObject'):
                print("IfcRelDefinesByObject")

            if (definition.is_a('IfcRelDefinesByObject') or definition.is_a('IfcRelDefinesByTemplate') or definition.is_a('IfcRelDefinesByType') or definition.is_a('IfcRelDefinesByProperties')) is False:
                print(definition.is_a())

        # Setting all the psets as a prim attribute
        # if we use namespaces to define also the single property set level
        # may cause errors because of characters not authorized in namespaces/key for attributes
        # but all chars are ok in the value field of the attribute

        self.usd_manager.create_prim_string_attribute(prim, "propertySets", property_sets_instance.toJSON(), self.base_namespace )
        self.usd_manager.create_prim_string_attribute(prim, "quantitySets", quantity_sets_instance.toJSON(), self.base_namespace )
        self.usd_manager.create_prim_string_attribute(prim, "ifcObjectInfo", object_info.toJSON(), self.base_namespace )

        #-----------------------HIERARCHY CONSTRUCTION -----------------------
        # follow Spatial relation
        if (ifc_element.is_a('IfcSpatialStructureElement')):
            # print(ifc_element.is_a(), " IfcSpatialStructureElement:")
            for rel in ifc_element.ContainsElements:
                relatedElements = rel.RelatedElements
                if relatedElements is None:
                    continue
                for child in relatedElements:
                    prim_as_parent = prim
                    self._create_ifc_hierarchy_in_usd(child,  prim_as_parent, stage)        
        # follow Aggregation Relation
        if (ifc_element.is_a('IfcObjectDefinition')):
            # print(ifc_element.is_a(), " IfcObjectDefinition:")
            for rel in ifc_element.IsDecomposedBy:
                relatedObjects = rel.RelatedObjects
                if relatedObjects is None:
                    continue
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
                lastMaterialId = materialId
                indicesSizeFoundWithLastMaterialId = 1

            m_i += 1

        return vectorWithMatIdsAndRelativeIndicesCount

    def fix_matrix(self, matrix):
        # matrix obtained by IFC are 3x4, we need 4x4 matrix
        matrix.insert(3, 0)
        matrix.insert(7, 0)
        matrix.insert(11, 0)
        matrix.insert(15, 1)
        return matrix

    def get_relative_texture_if_available(self, material_name):
        # here we check if in the same directory of IFC file there is an image/texture
        # that has the same name of the material passed as parameter
        # if there is, theorically this texture should be the one assigned to objects with this material

        # TODO: check if there is another more clear way to know if a ifc material has a related texture
        file_directory = os.path.dirname(self.ifc_manager.ifc_file_path)
        files_and_directories = os.listdir(file_directory)

        texture_file_path = [x for x in files_and_directories if x.startswith(material_name)]
        if len(texture_file_path) == 0:
            return None
        else:
            return texture_file_path[0]

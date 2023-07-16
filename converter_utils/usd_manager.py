from pxr import Usd, UsdGeom, Vt, Gf, Sdf, UsdShade
import re
from unidecode import unidecode
from converter_utils.timer import Timer

class UsdManager():
    def __init__(self, output_path):
        self.stage = Usd.Stage.CreateNew(output_path)

        

        self.guids_prims_dict = dict()
        
        
        world_prim_name = self.get_safe_prim_name(
            "World"
        )

        self.world_prim = self.stage.DefinePrim(world_prim_name)
        self.material_container_prim = self.define_container_prim("Materials")

        UsdGeom.SetStageUpAxis(self.stage, UsdGeom.Tokens.z)

        meter_per_unit = 1  # 1 unit equals 1 meters
        UsdGeom.SetStageMetersPerUnit(self.stage, meter_per_unit)

    #create a prim/node container inside world prim
    def define_container_prim(self, name):
        prim_path = str(self.world_prim.GetPath()) + self.get_safe_prim_name(name)
        container_prim = self.stage.DefinePrim(prim_path, "Scope")
        return container_prim
    
    def clear_prims_reference(self):
        self.guids_prims_dict = dict()
    
    def find_mesh_parent_prim_path(self, name):
        reference_prim = self.guids_prims_dict[name]
        reference_path = str(reference_prim.GetPath())
        return reference_path
    
    def create_prim(self, parent_prim, guid, prim_name, type = "Xform"):
        prim_complete_name = str(parent_prim.GetPath()) + self.get_safe_prim_name(prim_name)
        prim = self.stage.DefinePrim(prim_complete_name, type)
        self.guids_prims_dict[guid] = prim
        return prim

    def create_usd_mesh_(self, name, faces, vertices, matrix_4x4):
        mesh_reference_path = self.find_mesh_parent_prim_path(name)
        mesh = UsdGeom.Mesh.Define(self.stage, mesh_reference_path + "/Mesh_")
        # Set the subdivision scheme to None ( or Catmull-Clark)
        UsdGeom.Mesh(mesh).GetSubdivisionSchemeAttr().Set("none")

        # from list vertices to tuples of 3 elements
        vertices_tuple = tuple(
            vertices[e:e + 3] for e, k in enumerate(vertices) if e % 3 == 0)
        mesh.CreatePointsAttr().Set(Vt.Vec3fArray(vertices_tuple))

        # Set the face indices
        mesh.CreateFaceVertexIndicesAttr().Set(Vt.IntArray(faces))

        # Set the number of vertices per face (assuming it's a triangle mesh)
        faces_count = len(faces) / 3
        face_vertex_counts = [3] * int(faces_count)
        mesh.CreateFaceVertexCountsAttr().Set(face_vertex_counts)

        # Create an Xform matrix
        xform_matrix = Gf.Matrix4d(
            *matrix_4x4
        )

        # Create a transform #TODO: make it SRT? Scale, Rotate, Translate

        # give the transform to the parent of the meshs
        mesh_path = mesh.GetPath()
        mesh_prim = self.stage.GetPrimAtPath(mesh_path)
        mesh_parent = mesh_prim.GetParent()
        xformable = UsdGeom.Xformable(mesh_parent)

        xformable.MakeMatrixXform().Set(xform_matrix)

        return mesh

    def assign_mesh_material(self, usd_mesh, material_name, material_color, material_transparency):
         # Create a transparent material for the mesh
        material_path = str(self.material_container_prim.GetPath()) + self.get_safe_prim_name(material_name)
        material = UsdShade.Material.Define(self.stage,  material_path)

        # Create a surface shader
        surfaceShader = UsdShade.Shader.Define(self.stage, f"{material_path}/SurfaceShader")
        surfaceShader.CreateIdAttr("UsdPreviewSurface")
        surfaceShader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(material_color))
        surfaceShader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(material_transparency)  # Set the opacity value for transparency

        # Connect the surface shader to the material's surface output
        # Assign the material to the mesh
        material.CreateSurfaceOutput().ConnectToSource(surfaceShader.ConnectableAPI(), "surface")
        UsdShade.MaterialBindingAPI(usd_mesh).Bind(material)

    def assign_mesh_subset_material(self, usd_mesh, material_name, material_color, material_transparency, material_start_index_face_indices, material_indices_count ):
        material_path = str(self.material_container_prim.GetPath()) + self.get_safe_prim_name(material_name)

        
        material = UsdShade.Material.Define(self.stage,  material_path)

        # Create a new network for each material
        network = UsdShade.Shader.Define(self.stage, f"{material_path}/Network")
        network.CreateIdAttr("UsdPreviewSurface")
        network.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(material_color)
        network.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(material_transparency)  # Set the opacity value for transparency

        # Create a new subset for each material, if not already created
        subset_path = (str(usd_mesh.GetPath()) + '/Subset_' + self.get_safe_prim_name(material_name).replace('/',''))
        # print(subset_path)
        subset = self.stage.GetPrimAtPath(subset_path)
        if (subset.IsValid()):
            subset_indices = list(UsdGeom.Subset(subset).GetIndicesAttr().Get())
            subset_indices.extend(list(range(material_start_index_face_indices, material_start_index_face_indices + material_indices_count)))
            UsdGeom.Subset(subset).CreateIndicesAttr(subset_indices)
        else:
            subset = UsdGeom.Subset.Define(self.stage, usd_mesh.GetPath().AppendChild(f"Subset_{self.get_safe_prim_name(material_name).replace('/','')}"))
            subset_indices = list(range(material_start_index_face_indices, material_start_index_face_indices + material_indices_count))
            subset.CreateIndicesAttr(subset_indices)
            subset.CreateElementTypeAttr(UsdGeom.Tokens.face)
            material.CreateSurfaceOutput().ConnectToSource(network.ConnectableAPI(), "surface")
            UsdShade.MaterialBindingAPI(subset.GetPrim()).Bind(material)

        #subset = UsdGeom.Subset.Define(self.stage, usd_mesh.GetPath().AppendChild(f"Subset_{self.get_safe_prim_name(material_name).replace('/','')}"))
        #subset_indices = list(range(material_start_index_face_indices, material_start_index_face_indices + material_indices_count))#faces[start_index_face_indices * 3: (start_index_face_indices + material_indices_count) * 3]
        #subset.CreateIndicesAttr(subset_indices)
        #subset.CreateElementTypeAttr(UsdGeom.Tokens.face)

        #material.CreateSurfaceOutput().ConnectToSource(network.ConnectableAPI(), "surface")
        # start_index_face_indices += material_indices_count

        #UsdShade.MaterialBindingAPI(subset.GetPrim()).Bind(material)
            

    def set_mesh_transform(mesh, transform_matrix):
        mesh_transform = UsdGeom.Xformable(mesh)
        mesh_transform.AddTransformOp().Set(transform_matrix)

    def get_safe_prim_name(self, name):
        #name = re.sub("$","_dollar_", name)
        name = unidecode(name)
        name = "/" + re.sub("[^a-zA-Z0-9]", "_", name)
        return name

    def create_prim_string_attribute(self,prim, key, value, namespace):

        #make sure no spaces are passed in attribute name
        namespace = unidecode(namespace)
        key = unidecode(key)
        namespace = re.sub("[^a-zA-Z0-9]", "_", namespace)#namespace.replace(" ", "_").replace("(","").replace(")","")
        key = re.sub("[^a-zA-Z0-9]", "_", key)#key.replace(" ", "_").replace("(","").replace(")","")

        

        dataAttribute = prim.CreateAttribute(
            f"{namespace}:{key}",
            # Sdf.ValueTypeNames.String
            Sdf.ValueTypeNames.String
        )
        dataAttribute.Set(value)
        dataAttribute.SetVariability(Sdf.VariabilityUniform)

    def is_prim_already_created(self, parent_prim, prim_name):
        prim_complete_name = str(parent_prim.GetPath()) + self.get_safe_prim_name(prim_name)
        prim = self.stage.GetPrimAtPath(prim_complete_name)

        if prim.IsValid():
            return True
        else:
            return False
        
    def get_prim_if_created(self, parent_prim, prim_name):
        prim_complete_name = str(parent_prim.GetPath()) + self.get_safe_prim_name(prim_name)
        prim = self.stage.GetPrimAtPath(prim_complete_name)
        return prim

        

    def save_stage(self):
        self.stage.GetRootLayer().Save()
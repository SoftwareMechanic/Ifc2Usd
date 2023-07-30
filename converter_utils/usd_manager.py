from pxr import Usd, UsdGeom, Vt, Gf, Sdf, UsdShade, UsdPhysics
import re
from unidecode import unidecode


class UsdManager():
    def __init__(self, output_path):
        self.stage = Usd.Stage.CreateNew(output_path)

        # IFC use Z up, TODO: use parameter for output up axis?
        UsdGeom.SetStageUpAxis(self.stage, UsdGeom.Tokens.z)
        meter_per_unit = 1  # 1 unit equals 1 meters
        UsdGeom.SetStageMetersPerUnit(self.stage, meter_per_unit)

        # Dict used to map the prim created with the guid
        # Because we will need to add meshes to the stage, which have guid
        # of a node in the hierarchy created before geometry iteration
        self.guids_prims_dict = dict()

        # Creation of a world main node in the stage
        world_prim_name = self.get_safe_prim_name(
            "World"
        )
        self.world_prim = self.stage.DefinePrim(world_prim_name)

        # Create a folder for the Materials in the stage
        materials_prim_name = self.get_safe_prim_name(
            "Materials"
        )
        self.material_container_prim = self.stage.DefinePrim(materials_prim_name, "Scope")

    # create a prim/node container inside world prim
    def define_container_prim(self, name):
        world_path = str(self.world_prim.GetPath())
        container_prim_name = self.get_safe_prim_name(name)
        prim_path = world_path + container_prim_name
        container_prim = self.stage.DefinePrim(prim_path, "Scope")
        return container_prim

    def clear_prims_reference(self):
        self.guids_prims_dict = dict()

    def find_mesh_parent_prim_path(self, name):
        reference_prim = self.guids_prims_dict[name]
        reference_path = str(reference_prim.GetPath())
        return reference_path

    def create_prim(self, parent_prim, guid, prim_name, type="Xform"):
        parent_path = str(parent_prim.GetPath())
        safe_prim_name = self.get_safe_prim_name(prim_name)
        prim_complete_name = parent_path + safe_prim_name
        prim = self.stage.DefinePrim(prim_complete_name, type)
        self.guids_prims_dict[guid] = prim
        return prim

    def reuse_usd_mesh(self, name, mesh_to_reuse_prim_path):
        mesh_reference_path = self.find_mesh_parent_prim_path(name)
        mesh_prim = UsdGeom.Mesh.Define(self.stage, mesh_reference_path + "/Mesh_")
        mesh_prim.GetPrim().GetReferences().AddInternalReference(mesh_to_reuse_prim_path)
        return  UsdGeom.Mesh(mesh_prim)




    def set_usd_mesh(self, mesh, faces, vertices, matrix_4x4, uvs):
        mesh_path = mesh.GetPath()
        mesh_prim = self.stage.GetPrimAtPath(mesh_path)

        self.generate_mesh_vertices(mesh, vertices)
        self.generate_mesh_indices(mesh, faces)
        self.assign_transform_matrix(mesh_prim, matrix_4x4)
        self.generate_collider(mesh_prim)
        self.generate_uvs(mesh, uvs)

        return mesh

    def create_usd_mesh_(self, name):
        mesh_reference_path = self.find_mesh_parent_prim_path(name)
        mesh = UsdGeom.Mesh.Define(self.stage, mesh_reference_path + "/Mesh_")

        return mesh

    def assign_transform_matrix(self, prim, matrix_4x4):
        # Create an Xform matrix
        xform_matrix = Gf.Matrix4d(
            *matrix_4x4
        )

        # Create a transform #TODO: make it SRT? Scale, Rotate, Translate
        # mesh_parent = mesh_prim.GetParent()
        # xformable = UsdGeom.Xformable(mesh_parent)
        xformable = UsdGeom.Xformable(prim)
        xformable.MakeMatrixXform().Set(xform_matrix)

    def generate_uvs(self, mesh, uvs):
        uvs_tuple = tuple(
            uvs[e:e + 2] for e, k in enumerate(uvs) if e % 2 == 0)

        texCoords = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st",
                                                            Sdf.ValueTypeNames.TexCoord2fArray,
                                                            UsdGeom.Tokens.varying)
        texCoords.Set(uvs_tuple)

    def generate_collider(self, mesh_prim):
        # Set the type of collider (in this case, we use 'box')
        physics = UsdPhysics.CollisionAPI.Apply(mesh_prim)
        physics.CreateCollisionEnabledAttr()

    def generate_mesh_vertices(self, mesh, vertices):
        # from list vertices to tuples of 3 elements
        vertices_tuple = tuple(
            vertices[e:e + 3] for e, k in enumerate(vertices) if e % 3 == 0)
        mesh.CreatePointsAttr().Set(Vt.Vec3fArray(vertices_tuple))

    def generate_mesh_indices(self, mesh, faces):
        # Set the face indices
        mesh.CreateFaceVertexIndicesAttr().Set(Vt.IntArray(faces))

        # Set the number of vertices per face (assuming it's a triangle mesh)
        faces_count = len(faces) / 3
        face_vertex_counts = [3] * int(faces_count)
        mesh.CreateFaceVertexCountsAttr().Set(face_vertex_counts)

    def assign_mesh_material(self, usd_mesh, material_name, material_color, alpha):
        # Create a transparent material for the mesh
        material_container_path = str(self.material_container_prim.GetPath())
        safe_material_name = self.get_safe_prim_name(material_name)
        material_path = material_container_path + safe_material_name
        material = UsdShade.Material.Define(self.stage,  material_path)

        # Create a surface shader
        shader_path = f"{material_path}/SurfaceShader"
        surfaceShader = UsdShade.Shader.Define(self.stage, shader_path)
        surfaceShader.CreateIdAttr("UsdPreviewSurface")
        surfaceShader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(material_color))
        surfaceShader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(alpha)  # Set the opacity value for transparency

        # Connect the surface shader to the material's surface output
        # Assign the material to the mesh
        material.CreateSurfaceOutput().ConnectToSource(surfaceShader.ConnectableAPI(), "surface")
        UsdShade.MaterialBindingAPI(usd_mesh).Bind(material)

    def assign_mesh_subset_material(self, usd_mesh, material_name, material_color, alpha, material_start_index_face_indices, material_indices_count):
        # Define the material TODO: check if already exist
        material_container_path = str(self.material_container_prim.GetPath())
        material_prim_name = self.get_safe_prim_name(material_name)
        material_path = material_container_path + material_prim_name
       
        material = UsdShade.Material.Define(self.stage,  material_path)

        # Create a new network for each material
        network = UsdShade.Shader.Define(self.stage, f"{material_path}/Network")
        network.CreateIdAttr("UsdPreviewSurface")

        usd_diffuse = network.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f)
        usd_diffuse.Set(material_color)

        usd_opacity = network.CreateInput("opacity", Sdf.ValueTypeNames.Float)
        usd_opacity.Set(alpha)  # Set the opacity value for transparency

        # Create a new subset for the material, if not already created
        # we have to initialize it and define indices related to this subset
        # and bind the material to it
        # if already created we get it and extend the indices of that subset
        # otherwise considering we create subste with material name
        # the subset will be overwritten, causing a wrong material assignment
        usd_mesh_path = str(usd_mesh.GetPath())
        subset_name = self.get_safe_prim_name("Subset_" + material_name)
        subset_path = usd_mesh_path + subset_name
        subset = self.stage.GetPrimAtPath(subset_path)

        if (subset.IsValid()):
            subset_indices = list(UsdGeom.Subset(subset).GetIndicesAttr().Get())
            subset_indices_to_merge = list(
                range(
                    material_start_index_face_indices,
                    material_start_index_face_indices + material_indices_count
                    )
                )
            
            subset_indices.extend(subset_indices_to_merge)
            UsdGeom.Subset(subset).CreateIndicesAttr(subset_indices)
        else:
            subset = UsdGeom.Subset.Define(self.stage, subset_path)
            subset_indices = list(
                range(
                    material_start_index_face_indices,
                    material_start_index_face_indices + material_indices_count
                )
            )
            subset.CreateIndicesAttr(subset_indices)
            subset.CreateElementTypeAttr(UsdGeom.Tokens.face)
            material.CreateSurfaceOutput().ConnectToSource(network.ConnectableAPI(), "surface")
            UsdShade.MaterialBindingAPI(subset.GetPrim()).Bind(material)

    def set_mesh_transform(mesh, transform_matrix):
        mesh_transform = UsdGeom.Xformable(mesh)
        mesh_transform.AddTransformOp().Set(transform_matrix)

    def get_safe_prim_name(self, name):
        name = unidecode(name)
        name = "/" + re.sub("[^a-zA-Z0-9]", "_", name)
        return name

    def create_prim_string_attribute(self, prim, key, value, namespace):
        # make sure no spaces are passed in attribute name
        namespace = unidecode(namespace)
        key = unidecode(key)
        namespace = re.sub("[^a-zA-Z0-9]", "_", namespace)
        key = re.sub("[^a-zA-Z0-9]", "_", key)

        dataAttribute = prim.CreateAttribute(
            f"{namespace}:{key}",
            # Sdf.ValueTypeNames.String
            Sdf.ValueTypeNames.String
        )
        value = unidecode(value)
        dataAttribute.Set(value)
        dataAttribute.SetVariability(Sdf.VariabilityUniform)

    def is_prim_already_created(self, parent_prim, prim_name):
        parent_path = str(parent_prim.GetPath())
        safe_prim_name = self.get_safe_prim_name(prim_name)
        prim_path = parent_path + safe_prim_name
        prim = self.stage.GetPrimAtPath(prim_path)

        if prim.IsValid():
            return True
        else:
            return False

    def get_prim_if_created(self, parent_prim, prim_name):
        parent_path = str(parent_prim.GetPath())
        safe_prim_name = self.get_safe_prim_name(prim_name)
        prim_path = parent_path + safe_prim_name
        prim = self.stage.GetPrimAtPath(prim_path)
        return prim

    def save_stage(self):
        self.stage.GetRootLayer().Save()

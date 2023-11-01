import numpy as np


def weld_mesh(mesh_vertices, mesh_faces):
    """
    Given mesh vertices and faces return mesh vertices and faces welded
    """
    uniqueVertices_NewIndices = {}
    oldIndices_Vertices = {}
    verticesRemoved = 0
    newIndex = 0
    oldIndex = 0

    meshVertices = []

    for i in range(0, len(mesh_vertices), 3):
        x = mesh_vertices[i]
        y = mesh_vertices[i + 1]
        z = mesh_vertices[i + 2]

        vert = (x, y, z)
        if vert not in uniqueVertices_NewIndices:
            uniqueVertices_NewIndices[vert] = newIndex
            meshVertices.extend([float(x), float(y), float(z)])
            newIndex += 1

        oldIndices_Vertices[oldIndex] = vert
        oldIndex += 1

    verticesRemoved += oldIndex - newIndex
    faces = mesh_faces
    facesSize = len(faces)

    meshIndices = []

    for i in range(facesSize):
        index0 = mesh_faces[i]
        vert = oldIndices_Vertices[index0]
        newIndex0 = uniqueVertices_NewIndices[vert]
        meshIndices.append(newIndex0)

    return (meshVertices, meshIndices)


def switch_to_clockwise_order(vertices):
    if len(vertices) != 3:
        raise ValueError("La funzione richiede esattamente tre vertici")

    vector_AB = (vertices[1][0] - vertices[0][0], vertices[1][1] - vertices[0][1])
    vector_BC = (vertices[2][0] - vertices[1][0], vertices[2][1] - vertices[1][1])

    # Calculate the cross product of AB and BC
    cross_product = vector_AB[0] * vector_BC[1] - vector_AB[1] * vector_BC[0]
    cross_product = crossProd(vertices[0], vertices[1])

    # If the cross product is positive, it's in anticlockwise order; otherwise, it's not

    print(cross_product)

    if cross_product > 0:
       pass
        #print("Triangle is counterclockwise")
    elif cross_product < 0:
        print("Triangle is clockwise")
    else:
        print("Triangle is degenerate (collinear)")
    print(cross_product > 0)

    is_anti_clockwise = cross_product > 0
    

    # import numpy as np

    # x = [vertices[0]]
    # y = [vertices[1]]
    # z = [vertices[2]]

    if is_anti_clockwise:
        #print("antiorario trovato = ", vertices)
        return [vertices[2], vertices[0], vertices[1]]
    else:
        return vertices  # Gli vertici sono già in ordine orario

def is_anti_clockwise2(triangle):
    vector_AB1 = (triangle[1][0] - triangle[0][0], triangle[1][1] - triangle[0][1])
    vector_BC1 = (triangle[2][0] - triangle[1][0], triangle[2][1] - triangle[1][1])
    cross_product1 = vector_AB1[0] * vector_BC1[1] - vector_AB1[1] * vector_BC1[0]

    return cross_product1


def get_normal(triangle):
    vertex1 = np.array([triangle[0][0], triangle[0][1], triangle[0][2]])
    vertex2 = np.array([triangle[1][0], triangle[1][1], triangle[1][2]])
    vertex3 = np.array([triangle[2][0], triangle[2][1], triangle[2][2]])

    # Calculate two vectors along the edges of the triangle
    vector1 = vertex2 - vertex1
    vector2 = vertex3 - vertex1

    # Calculate the normal vector using the cross product of vector1 and vector2
    normal = np.cross(vector1, vector2)

    # Normalize the normal vector (optional but recommended)
    normal /= np.linalg.norm(normal)

    return normal


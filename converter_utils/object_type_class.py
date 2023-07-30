import json


class ObjectInfo():
    GUID = ""
    IfcEntity = ""
    IfcType = ""
    Name = ""
    Tag = ""
    ElementType = ""
    PredefinedType = ""
    ConstructionType = ""
    OperationType = ""
    Description = ""
    OverallHeight = ""
    OverallWidth = ""
    #ObjectPlacement = ""
    ObjectType = ""

    def __init__(self):
        self.GUID = ""
        self.IfcEntity = ""
        self.IfcType = ""
        self.Name = ""
        self.Tag = ""
        self.ElementType = ""
        self.PredefinedType = ""
        self.ConstructionType = ""
        self.OperationType = ""
        self.Description = ""
        self.OverallHeight = ""
        self.OverallWidth = ""
        #ObjectPlacement = ""
        self.ObjectType = ""
        pass

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
                          sort_keys=True, indent=4)
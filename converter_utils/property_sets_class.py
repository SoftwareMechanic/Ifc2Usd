import json

class PropertySets():
    
    def __init__(self):
        self.property_sets = []
        pass
        

    def toJSON(self):
        return json.dumps(self.property_sets, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)

class PropertySet():
    def __init__(self, name):
        self.name = name
        self.properties = dict()

    

    

import json


class QuantitySets():
    def __init__(self):
        self.quantity_sets = []
        pass
        
    def toJSON(self):
        return json.dumps(self.quantity_sets,
                          default=lambda o: o.__dict__,
                          sort_keys=True,
                          indent=4)


class QuantitySet():
    def __init__(self, name):
        self.Name = name
        # self.properties = dict()
        self.Properties = []


class QuantityProperty():
    def __init__(self, name, type, unit, value):
        self.Name = name
        self.Type = type
        self.Unit = unit
        self.Value = value


    

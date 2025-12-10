import json 
def read_json(dir):
    with open(dir, 'r') as f:
        data = json.load(f)
    return data
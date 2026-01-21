import json

with open("f-80a.txt","r") as file:
    data = json.load(file)
        
        
for key,value in data[0]["Full"].items():
    print(key)
        
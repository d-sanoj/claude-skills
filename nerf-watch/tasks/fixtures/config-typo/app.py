import json

config = json.load(open("config.json"))
print("connecting to", config["database"])
print("ready")

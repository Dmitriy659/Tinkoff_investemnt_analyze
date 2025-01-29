import json
import os

config_path = os.path.join(os.path.dirname(__file__), 'settings.json')

file = open(config_path)
data = json.load(file)
TOKEN = data['TOKEN']
file.close()

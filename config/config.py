import yaml
import os

# Get the directory where this config.py file is located
config_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(config_dir, 'config.yaml')

with open(config_path, 'r') as configFile:
    config = yaml.safe_load(configFile)
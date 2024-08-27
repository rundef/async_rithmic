import os
import importlib

# Get the directory path of the current file
package_dir = os.path.dirname(__file__)

# Loop through all files in the directory
for filename in os.listdir(package_dir):
    # Import any Python files except __init__.py
    if filename.endswith('.py') and filename != '__init__.py':
        module_name = filename[:-3]  # Remove the .py extension
        # Import the module dynamically
        importlib.import_module(f'.{module_name}', package=__name__)

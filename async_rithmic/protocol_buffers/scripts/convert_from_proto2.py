import os
import re
import shutil


# Function to convert proto2 to proto3
def convert_proto2_to_proto3(proto_file_path):
    with open(proto_file_path, 'r') as file:
        content = file.readlines()

    converted_content = []
    syntax_set = False
    for line in content:
        # Change syntax declaration
        if line.strip().startswith('syntax = "proto2";'):
            converted_content.append('syntax = "proto3";\n')
            syntax_set = True
        # Ensure syntax is set
        elif line.strip().startswith('syntax = "proto3";'):
            syntax_set = True
            converted_content.append(line)
        # Remove 'optional' and 'required' keywords
        elif 'optional ' in line or 'required ' in line:
            converted_content.append(line.replace('optional ', '').replace('required ', ''))
        # Remove default values (optional)
        elif 'default = ' in line:
            converted_content.append(line.split(' [default = ')[0] + ';\n')
        else:
            converted_content.append(line)

    # Add syntax declaration if not found
    if not syntax_set:
        converted_content.insert(0, 'syntax = "proto3";\n')

    with open(proto_file_path, 'w') as file:
        file.writelines(converted_content)


# Function to update enums to ensure the first value is zero
def update_enum(proto_file_path):
    with open(proto_file_path, 'r') as file:
        content = file.read()

    # Regular expression to find enums
    enum_pattern = re.compile(r'enum\s+\w+\s*{[^}]*}', re.MULTILINE)
    enums = enum_pattern.findall(content)

    for enum in enums:
        # Check if the first value is zero
        enum_lines = enum.split('\n')
        first_value = re.search(r'=\s*(\d+)', enum_lines[1])
        if first_value and first_value.group(1) != '0':
            enum_name = re.search(r'enum\s+(\w+)', enum).group(1)
            new_enum = enum_lines[:1]
            new_enum.append(f'    {enum_name.upper()}_UNSPECIFIED = 0;')
            new_enum.extend(enum_lines[1:])
            new_enum_str = '\n'.join(new_enum)
            content = content.replace(enum, new_enum_str)

    with open(proto_file_path, 'w') as file:
        file.write(content)


# Directory paths
source_proto_dir = '../protobuf2'
target_proto_dir = '../source'

# Create the target directory if it doesn't exist
if not os.path.exists(target_proto_dir):
    os.makedirs(target_proto_dir)

# Copy and convert all .proto files from the source directory to the target directory
for root, _, files in os.walk(source_proto_dir):
    for file in files:
        if file.endswith('.proto'):
            # Construct full file path
            source_file_path = os.path.join(root, file)
            relative_path = os.path.relpath(source_file_path, source_proto_dir)
            target_file_path = os.path.join(target_proto_dir, relative_path)

            # Ensure target directory exists
            os.makedirs(os.path.dirname(target_file_path), exist_ok=True)

            # Copy file to target directory
            shutil.copyfile(source_file_path, target_file_path)

            # Convert and update the .proto file
            convert_proto2_to_proto3(target_file_path)
            update_enum(target_file_path)

print(f'Conversion completed. The converted files are in the directory: {target_proto_dir}')

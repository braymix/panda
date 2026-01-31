python
import os
import re

def clean_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.readlines()

    new_content = []
    in_code_block = False
    skip_lines = False

    for line in content:
        if in_code_block:
            new_content.append(line)
            if line.strip().endswith('
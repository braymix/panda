python
import os
import re

def is_code_block(line):
    return line.strip().startswith('
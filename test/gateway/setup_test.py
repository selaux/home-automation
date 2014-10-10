import sys
from os import path

def setup():
    gateway_path = path.realpath(path.abspath(path.join(__file__, '../../../gateway/')))
    if not gateway_path in sys.path:
        sys.path.append(gateway_path)

import os
import yaml
import logging


from PyLTSpice import SimCommander
from PyLTSpice import RawRead

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_ltspice_config(config_path='config/config.yaml'):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    
    ltspice_path = config.get('ltspice_executable', None)
    if ltspice_path is None:
        raise ValueError("LTspice executable path not found in configuration file.")
    
    base_directory = config.get('base_directory', None)

    return ltspice_path, base_directory

def create_simulation_object(ltspice_path, asc_file_path):
    if not os.path.exists(ltspice_path):
        raise FileNotFoundError(f"LTspice executable not found: {ltspice_path}")
    if not os.path.exists(asc_file_path):
        raise FileNotFoundError(f".asc file not found: {asc_file_path}")

    sim = SimCommander(ltspice_path, asc_file_path)
    return sim


def load_simulation_results(asc_file_path):
    raw_file_path = os.path.splitext(asc_file_path)[0] + "_1.raw"
    logger.info(f"Checking .raw file: {raw_file_path}")
    if not os.path.exists(raw_file_path):
        raise RuntimeError(f"Raw file not generated: {raw_file_path}")

    raw = RawRead(raw_file_path)
    signals = raw.get_trace_names()
    logger.info(f"Available signals: {signals}")
    
    return raw


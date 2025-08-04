#!/usr/bin/env python3
import os
import argparse
import sys
import traceback
from dataclasses import dataclass
import struct
import yaml
import logging
import csv
from datetime import datetime

# This script uses a state-based approach to correctly parse Rogue .dat files.
# It maintains a complete state of the system and logs a snapshot whenever
# the main timestamp is updated.

# --- Configuration & Setup ---
RogueHeaderSize = 8
RogueHeaderPack = 'IHBB'

@dataclass
class RogueHeader:
    size: int
    flags: int
    error: int
    channel: int

def get_nested_value(d, path, default=None):
    """
    Safely gets a value from a nested dictionary using a dot-separated path
    that can include list indices like 'PrbsRx[0]'.
    """
    keys = path.split('.')
    for key in keys:
        try:
            if '[' in key and key.endswith(']'):
                name, index_str = key.split('[')
                index = int(index_str[:-1])
                d = d[name][index] # Access list by name, then element by index
            else:
                d = d[key] # Standard dictionary access
        except (KeyError, IndexError, TypeError, AttributeError):
            return default
    return d

def set_nested_value(d, path, value):
    """
    Safely sets a value in a nested dictionary using a dot-separated path
    that can include list indices like 'PrbsRx[0]', creating structure as needed.
    """
    keys = path.split('.')
    for key in keys[:-1]: # Iterate to the second-to-last key
        if '[' in key and key.endswith(']'):
            name, index_str = key.split('[')
            index = int(index_str[:-1])
            
            # Ensure the list exists and is long enough
            if name not in d or not isinstance(d.get(name), list):
                d[name] = []
            while len(d[name]) <= index:
                d[name].append({}) # Append dicts for future keys
            
            d = d[name][index]
        else:
            d = d.setdefault(key, {})

    # Set the final value on the last key
    last_key = keys[-1]
    if '[' in last_key and last_key.endswith(']'):
        name, index_str = last_key.split('[')
        index = int(index_str[:-1])
        if name not in d or not isinstance(d.get(name), list):
            d[name] = []
        while len(d[name]) <= index:
            d[name].append(None)
        d[name][index] = value
    else:
        # Check if d is a dictionary before setting the key
        if isinstance(d, dict):
            d[last_key] = value
        # If d is not a dict (e.g., it's a list we navigated into), this indicates a path issue.
        # This case should ideally not be hit with correct paths.

# --- Argument Parser ---
parser = argparse.ArgumentParser(
    description="Extracts and logs specific variables from a Rogue .dat file to a CSV."
)
parser.add_argument('data_file', type=str, help="Path to the input .dat file.")
parser.add_argument('--csv', type=str, default='log_output.csv', help="Name of the output CSV file.")
parser.add_argument('--chan', type=int, default=0, help="Config stream channel ID.")
args = parser.parse_args()

# --- Main Application ---
if not os.path.exists(args.data_file):
    print(f"Error: Data file '{args.data_file}' not found.")
    exit()

print(f"--- Analyzing data from {args.data_file} ---")

# 1. Initialize the state dictionary and the list for CSV rows
current_state = {}
log_rows = []
csv_headers = [
    'Timestamp', 'WordErrCnt', 'EofeErrCnt',
    'MissedPacketCnt', 'LinkErrorCnt', 'FrameCnt'
]

try:
    with open(args.data_file, 'rb') as f:
        file_size = os.path.getsize(args.data_file)
        
        while f.tell() < file_size:
            header_bytes = f.read(RogueHeaderSize)
            if len(header_bytes) < RogueHeaderSize: break

            header = RogueHeader(*struct.unpack(RogueHeaderPack, header_bytes))
            payload_size = header.size - 4

            if header.channel == args.chan:
                yaml_bytes = f.read(payload_size)
                try:
                    config_update = yaml.safe_load(yaml_bytes.decode('utf-8'))
                    if not isinstance(config_update, dict): continue

                    old_time = get_nested_value(current_state, 'Root.Time', 0.0)

                    # Update state from the new YAML data
                    for key, value in config_update.items():
                        set_nested_value(current_state, key, value)
                    
                    new_time = get_nested_value(current_state, 'Root.Time', 0.0)

                    # If the timestamp has changed, log a row
                    if new_time > old_time:
                        word_err = get_nested_value(current_state, 'Root.App.PrbsRx[0].WordErrCnt', 'N/A')
                        eofe_err = get_nested_value(current_state, 'Root.App.PrbsRx[0].EofeErrCnt', 'N/A')
                        missed_pkt = get_nested_value(current_state, 'Root.App.PrbsRx[0].MissedPacketCnt', 'N/A')
                        link_err = get_nested_value(current_state, 'Root.App.Pgp4AxiL[0].RxStatus.LinkErrorCnt', 'N/A')
                        frame_cnt = get_nested_value(current_state, 'Root.App.PrbsRx[0].FrameCnt', 'N/A')
                        
                        log_rows.append([
                            datetime.fromtimestamp(new_time).strftime('%Y-%m-%d %H:%M:%S.%f'),
                            word_err, eofe_err, missed_pkt, link_err, frame_cnt
                        ])

                except (yaml.YAMLError, UnicodeDecodeError) as e:
                    pass # Silently ignore frames that can't be parsed
            else:
                f.seek(payload_size, 1) # Skip non-config frames

except Exception as e:
    print("\nAn error occurred during file processing:")
    traceback.print_exc()

# 6. Save the collected data to a CSV file
if not log_rows:
    print("\nAnalysis complete. No timestamped log points were found.")
else:
    print(f"\nAnalysis complete. Found {len(log_rows)} valid log points.")
    print(f"Saving data to {args.csv}...")
    
    try:
        with open(args.csv, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(csv_headers)
            writer.writerows(log_rows)
        print("File saved successfully.")
    except Exception as e:
        print(f"Error saving file: {e}")


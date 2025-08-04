#!/usr/bin/env python3
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import time

# --- Argument Parser Setup ---
parser = argparse.ArgumentParser(
    description="Generates a 3-panel plot to visualize link integrity against environmental temperature."
)
parser.add_argument(
    'link_data_csv',
    type=str,
    help="Path to the CSV file containing the logged link/error counts (e.g., 'log_output.csv')."
)
parser.add_argument(
    'temp_data_csv',
    type=str,
    help="Path to the CSV file containing the environmental temperature data."
)
parser.add_argument(
    '--start_time',
    type=str,
    default='13:22:00',
    help="Start time for the plot in HH:MM:SS format. Defaults to '13:22:00'."
)
parser.add_argument(
    '--end_time',
    type=str,
    default='15:00:00',
    help="End time for the plot in HH:MM:SS format. Defaults to '15:00:00'."
)
parser.add_argument(
    '--save',
    type=str,
    default=None,
    help="Save the plot to a file (e.g., 'link_integrity_plot.png')."
)
args = parser.parse_args()


# --- Data Loading and Processing ---

try:
    # 1. Load the link integrity data
    print(f"Loading link data from: {args.link_data_csv}")
    link_df = pd.read_csv(args.link_data_csv)
    link_df['Timestamp'] = pd.to_datetime(link_df['Timestamp'])

    counter_cols = ['WordErrCnt', 'EofeErrCnt', 'MissedPacketCnt', 'LinkErrorCnt', 'FrameCnt']
    for col in counter_cols:
        link_df[col] = pd.to_numeric(link_df[col], errors='coerce').fillna(0)

    # 2. Load the environmental temperature data
    print(f"Loading temperature data from: {args.temp_data_csv}")
    temp_df = pd.read_csv(args.temp_data_csv)
    temp_df.rename(columns={'Time': 'Timestamp', 'value': 'Temperature'}, inplace=True)
    temp_df['Timestamp'] = pd.to_datetime(temp_df['Timestamp'])
    temp_df['Temperature'] = temp_df['Temperature'].str.replace(' K', '', regex=False)
    temp_df['Temperature'] = pd.to_numeric(temp_df['Temperature'], errors='coerce')

    # 3. Filter data to be within the specified time range
    start_time = pd.to_datetime(args.start_time).time()
    end_time = pd.to_datetime(args.end_time).time()
    print(f"Filtering data to include timestamps from {start_time} to {end_time}.")
    
    link_df = link_df[(link_df['Timestamp'].dt.time >= start_time) & (link_df['Timestamp'].dt.time <= end_time)]
    temp_df = temp_df[(temp_df['Timestamp'].dt.time >= start_time) & (temp_df['Timestamp'].dt.time <= end_time)]

    if link_df.empty:
        print("Warning: No link data remains after applying the time filter.")
    if temp_df.empty:
        print("Warning: No temperature data remains after applying the time filter.")

except FileNotFoundError as e:
    print(f"Error: Could not find a file. Please check your paths.\nDetails: {e}")
    exit()
except Exception as e:
    print(f"An error occurred while processing the data files.\nDetails: {e}")
    exit()


# --- Plotting ---

print("Generating plot...")

# Define bold font properties
font_props = {'fontweight': 'bold'}

# 1. Create a figure and a set of 3 stacked subplots that share the same X-axis
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(16, 12), sharex=True, 
                                    gridspec_kw={'height_ratios': [3, 2, 3]})
fig.suptitle(f'Cryo Loopback Test: \nTime vs. Frame Count, Error Counts, and Temperature', fontsize=20, **font_props)

# 2. Top Panel: Frame Count
ax1.plot(link_df['Timestamp'], link_df['FrameCnt'], color='dodgerblue')
ax1.set_ylabel('Frame Count', **font_props)
ax1.set_title('Total Received Frames', **font_props)
ax1.grid(True, linestyle='--', alpha=0.6)
ax1.ticklabel_format(style='sci', axis='y', scilimits=(0,0))
for label in ax1.get_yticklabels():
    label.set_fontweight('bold')

# 3. Middle Panel: Link Integrity (Error Counts)
ax2.plot(link_df['Timestamp'], link_df['WordErrCnt'], label='WordErrCnt', color='red')
ax2.plot(link_df['Timestamp'], link_df['EofeErrCnt'], label='EofeErrCnt', color='orange')
ax2.plot(link_df['Timestamp'], link_df['MissedPacketCnt'], label='MissedPacketCnt', color='purple')
ax2.plot(link_df['Timestamp'], link_df['LinkErrorCnt'], label='LinkErrorCnt', color='brown')
ax2.set_ylabel('Count', **font_props)
ax2.set_title('Error Counts (WordErrCnt, EofeErrCnt, MissedPacketCnt, LinkErrorCnt)', **font_props)
ax2.grid(True, linestyle='--', alpha=0.6)
ax2.legend()
# Set a tight y-axis limit to emphasize that the counts are zero
ax2.set_ylim(-1, 10)
for label in ax2.get_yticklabels():
    label.set_fontweight('bold')


# 4. Bottom Panel: Temperature
ax3.plot(temp_df['Timestamp'], temp_df['Temperature'], color='green')
ax3.set_ylabel('Temperature (K)', **font_props)
ax3.set_title('Environmental Chamber Temperature', **font_props)
ax3.grid(True, linestyle='--', alpha=0.6)
for label in ax3.get_yticklabels():
    label.set_fontweight('bold')

# 5. Final Formatting for the shared X-axis
ax3.set_xlabel('Time', **font_props)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
for label in ax3.get_xticklabels():
    label.set_fontweight('bold')
fig.autofmt_xdate()

# Adjust layout to prevent titles/labels from overlapping
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# 6. Show or Save the plot
if args.save:
    try:
        plt.savefig(args.save, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {args.save}")
    except Exception as e:
        print(f"Error saving plot: {e}")
else:
    print("Displaying plot...")
    plt.show()


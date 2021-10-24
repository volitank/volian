from platform import architecture
from utils import ask, byte_to_gig_trunc
from pathlib import Path
from constant import ROOT_BASHRC, ROOT_DIR, ESP_SIZE_M, BOOT_SIZE_M, VOLIAN_LOG
from collections import Counter
from subprocess import run, STDOUT
from typing import TextIO

def print_part_layout(part_list: list, space_left: int):
	"""Takes a list of tuples and prints the layout

	Tupels in the list should consist of (path, size, filesystem)
	
	"""
	# Print our layout to the user so they can check it over

	column_list = []
	# Iterate through our list
	for part in part_list:
		for item in part:
			# Make a list of how big the strings are to be printed
			length = len(str(item))
			# Append them to our list
			column_list.append(length)
	# Define the width of our columns plus a pad using the largest size from our list
	col_width = max(column_list) + 1

	# Print our header
	print(
		"Mount:".ljust(col_width),
		"Filesystem:".ljust(col_width),
		"Size:".ljust(col_width),
	)
	# Iterate through the part list once more
	for part in part_list:
		path, size, fs = part
		# If the size is free change it to remaining space
		if size == '100%FREE':
			size = space_left
		# Print our parts with our column width
		print(
			str(path).ljust(col_width),
			str(fs).ljust(col_width),
			str(byte_to_gig_trunc(size))+' GB'.ljust(col_width)
		)

part_list = [(Path('/boot/efi'), 536870912, 'fat32'), (Path('/boot'), 1610612736, 'ext2'),
			(Path('/'), 21474836480, 'ext4'), (Path('/var'), 21474836480, 'ext4'), (Path('/home'), '100%FREE', 'ext4'),
			(Path('/srv/volicloud'), 21474836480, 'ext4')]

print_part_layout(part_list, 10240000000)


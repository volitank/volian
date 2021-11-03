# This file is part of volian

# volian is an installer for Debian or Ubuntu.
# Copyright (C) 2021 Volitank

# volian is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# volian is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with volian.  If not, see <https://www.gnu.org/licenses/>.

if __name__ == "__main__":
	print("partition isn't intended to be run directly.. exiting")
	exit(1)

from collections import Counter
from os import PathLike
from pathlib import Path
from time import sleep
from typing import Union


from logger import eprint 
from constant import FILESYSTEMS, FSTAB_FILE, FSTAB_HEADER, ROOT_DIR, BOOT_DIR, EFI_DIR
from utils import byte_to_gig_trunc, ask, meg_to_byte, gig_to_byte, ask_list, shell, DEFAULT

def define_partitions():
	"""Main function for defining partitions. Takes no arguments and returns a list of tuples, disk, and the space left on disk

	tuples contain (path, size, filesystem). space_left is in bytes
	"""
	while True:
		# We wrap the entire function in a try except to handle Ctrl+C
		# Which wil restart the function
		try:
			# Restart switch is used later to handle deep errors and bounce back to this loop
			_restart_switch = False
			# No print is so we don't print the partition layout more than once if we configure custom parts.
			_no_print = False
			disk = choose_disk()
			true_size = (float(Path(f"/sys/block/{disk.name}/size").read_text()) * 512)
			#space_left = true_size - (ESP_SIZE_M + BOOT_SIZE_M)
			space_left = true_size
			# When using our installer defining root, esp and boot are not optional
			# Tuple is (path, size, filesystem, lv_name)

			esp_partition, space_left = ask_part_size(Path('/boot/efi'), space_left, disk)
			boot_partition, space_left = ask_part_size(Path('/boot/'), space_left, disk)
			root_partition, space_left = ask_part_size(Path('/'), space_left)

			# Part list is going to be our list that we use for operations.
			part_list = [root_partition, boot_partition, esp_partition]
			# This list is only for making sure we aren't defining duplicate mount points.
			_path_list = [root_partition.path, boot_partition.path, esp_partition.path]

			if ask("Do you want to configure any custom partitions"):
				while True:
					# Get the path that the user would like to configure
					path = Path('/'+input("enter the path you'd like to configure: /"))
					# After the user defines a part add it to our checking list.
					_path_list.append(path)

					# Dupe_path is going to be a list filled with any duplicates from _path_list
					dupe_path = [k for k,v in Counter(_path_list).items() if v>1]
					# If we have duplicates then we will throw an error and restart the partitioner
					if dupe_path:
						print()
						eprint(f"you can't define '{dupe_path[0]}' more than once")
						eprint(f"restarting partitioner..\n")
						sleep(2)
						print()
						_restart_switch = True
						break
					
					# Send the user defined path and the space we have left over to our part size function
					new_partition, space_left = ask_part_size(path, space_left)

					# Add that new partition to our list.
					part_list.append(new_partition)
					part_list.sort

					# Check if theydefined free more than once.
					free_check = []
					for partition in part_list:
						free_check.append(partition.size)
					if str(free_check).count('100%FREE') > 1:
						print()
						eprint("you can't have 100%free defined twice.")
						eprint(f"restarting partitioner..\n")
						sleep(2)
						print()
						_restart_switch = True
						break

					# Print our layout to the user so they can check it over
					print_part_layout(part_list, space_left)
					_no_print = True

					# Ask them if they want to restart the loop, break if they don't
					if not ask("would you like to configure additional partitions"):
						break

			if _restart_switch:
				continue
			if not _no_print:
				# Print our layout to the user so they can check it over
				print_part_layout(part_list, space_left)

			if ask("Is this layout okay"):
				# Iterate through the list and bring 100%FREE to the last
				# We need free to be at the end for LVM creation
				for n in range(0, len(part_list)):
					if part_list[n].size == '100%FREE':
						part_list.append(part_list.pop(n))
				return part_list, disk, space_left

		# Using Ctrl+C will restart the partitioner
		except KeyboardInterrupt:
			print("\nrestarting partitioner..\n")
			# We set a sleep so you can Ctrl+C again to exit the function
			sleep(2)
			continue

def choose_disk():
	'Asks user for block device. Returns Path object'
	# There may be a better way of getting disks that are applicable but for now this works.
	#data = run(["lsblk", "-pro", "NAME,TYPE,SIZE,MOUNTPOINT"], capture_output=True).stdout.decode().strip().split('\n')
	data = shell.lsblk._pro('NAME,TYPE,SIZE,MOUNTPOINT', logfile=DEFAULT, capture_output=True).stdout.decode().strip().split('\n')
	for i in data:
		if 'disk' in i:
			print(i)
	while True:
		disk = Path('/dev/'+input("Which disk you would like to use? /dev/"))

		if not disk.is_block_device():
			eprint(f"{disk} is not a block device")
			continue

		if disk.exists():
			return disk
		else:
			eprint(f"{disk} doesn't exist")

def filter_input(unknown):
	'convert input to byte from meg or gig'
	# This was made specifically for ask_part_size function
	try:
		if 'M' in unknown:
			return int(meg_to_byte(float(unknown.rstrip('M'))))
		elif 'G' in unknown:
			return int(gig_to_byte(float(unknown.rstrip('G'))))
		else:
			raise ValueError
	except (ValueError, TypeError):
		eprint("Invalid input")
		return False

def ask_part_size(part_path: str, size: int, disk=None):
	"""Function for determining if, and what size parts to make

	Arguments:
		part_path: should be simple name of part such as 'root' or 'home' or Path object
		size: free space left on the block device as an integer in bytes
	
	returns (name, size), space_left
	"""
	while True:
		try:
			human = byte_to_gig_trunc(size)
			# Make the size human readable. and then ask them how big they want the partition. 
			human_part_size = input(f"\n{human} GB of disk space remains\nHow much space would you like to allocate to\n{part_path} ? [512M, 10G, free] ")
			if human_part_size in ('free', 'Free'):
				part_size = '100%FREE'

			# Figure out if they gave us Megabyte or Gigabyte and then convert it to byte
			elif filter_input(human_part_size):
				part_size = filter_input(human_part_size)
				if part_size > size:
					eprint(f"{human_part_size} GB is more than you have left.. try again")
			else:
				continue
			# Now we can iterate through our paths an generate an LV name based on it
			# For boot_efi and boot these names are only for identification
			# Let us name root appropriately 
			if str(part_path) == '/':
				lv_name = 'root'
			# Incase someone tries to create a root home this won't break anything
			elif str(part_path) == '/root':
				lv_name = 'roothome'
			# Everything else will be named according to their path minus the first slash
			# All remaining slashes will be replaced with an underscore '/srv/volian' becomes 'srv_volian'
			else:
				lv_name = str(part_path).lstrip('/').replace('/', '_')

			# Handle our special efi and boot scenarios	
			boot = None
			efi = None

			if lv_name == 'boot_efi':
				efi = Path(str(disk)+'1')
				filesystem = 'fat32'
			else:
				filesystem = ask_list(FILESYSTEMS, 'filesystem')
			
			if lv_name == 'boot':
				boot = Path(str(disk)+'2')

			part_object = partition(part_path, part_size, filesystem, lv_name, efi, boot)
			try:
				return part_object, (size - part_size)
			except TypeError:
				return part_object, size

		except ValueError:
			eprint(f"that isn't a valid number")

def print_part_layout(part_list: list, space_left: int):
	"""Takes a list of tuples and prints the layout

	Tupels in the list should consist of (path, size, filesystem)
	
	"""
	# Print our layout to the user so they can check it over

	column_list = []
	# Iterate through our list
	for partition in part_list:
		# Append the length of each string to our list
		column_list.append(len(str(partition.name)))
		column_list.append(len(str(partition.size)))
		column_list.append(len(str(partition.path)))
		column_list.append(len(str(partition.filesystem)))
	# Define the width of our columns plus a pad using the largest size from our list
	col_width = max(column_list) + 1

	# Print our header
	print(
		"Mount:".ljust(col_width),
		"Filesystem:".ljust(col_width),
		"Size:".ljust(col_width),
	)
	# Iterate through the part list once more
	for partition in part_list:
		size = partition.size
		# If the size is free change it to remaining space
		if partition.size == '100%FREE':
			# We can't just use partition.size because we can't update the variable
			size = space_left
		# Print our parts with our column width
		print(
			str(partition.path).ljust(col_width),
			str(partition.filesystem).ljust(col_width),
			str(byte_to_gig_trunc(size))+' GB'.ljust(col_width)
		)

def write_fstab(boot_uuid: str, efi_uuid: str, volume: str, part_list: list):
	"""Function for encrypting a block device.

	Arguments:
		efi_uuid: The UUID of the EFI partition. Example '6DDB-7DBB'
		boot_uuid: The UUID of the boot partition. Example '8e1fdc49-4a15-41cc-bf87-799954c039ad'
		volume: The name of the volume group. Example 'debianvg'
		part_list: This is our list of tuples from the partition setup
	"""
	fstab_list = [("# <file system>","<mount point>","<type>","<options>","<dump>","<pass>")]

	# This should be fine to iterate because the first three should always be in this order
	for partition in part_list:
		if partition.name == 'root':
			iter_tupe = (
					f"/dev/mapper/{volume}-{partition.name}",
					str(partition.path),partition.filesystem,"errors=remount-ro","0","1")
		elif partition.name == 'boot':
			iter_tupe = (f"UUID={boot_uuid}",
						str(partition.path),partition.filesystem,"defaults","0","2")
		elif partition.name == 'boot_efi':
			iter_tupe = (f"UUID={efi_uuid}",
						str(partition.path),"vfat","umask=0077","0","1")
		else:
			iter_tupe = (f"/dev/mapper/{volume}-{partition.name}",
						str(partition.path),partition.filesystem,"defaults","0","2")

		fstab_list.append(iter_tupe)

	device_list = []
	mount_list = []
	options_list = []
	# Iterate through our list
	for line in fstab_list:
		device = line[0]
		mount = line[1]
		options = line[3]
		# Make a list of how big the strings are to be printed
		device_length = len(str(device))
		mount_length = len(str(mount))
		options_length = len(str(options))
		# Append them to our list
		device_list.append(device_length)
		mount_list.append(mount_length)
		options_list.append(options_length)

	# Define the width of our columns plus a pad using the largest size from our list
	device_width = max(device_list) + 1
	mount_width = max(mount_list) + 1
	options_width = max(options_list) + 1

	with open(FSTAB_FILE, 'w') as fstab_file:
		fstab_file.write(FSTAB_HEADER)

		# root, boot, efi should be in that order.
		for line in fstab_list:
			device, mount, fs, options, dump, _pass = line
			print(
				str(device).ljust(device_width),
				str(mount).ljust(mount_width),
				str(fs).ljust(8),
				str(options).ljust(options_width),
				str(dump).ljust(8),
				str(_pass).ljust(2),
				file=fstab_file
				)

class partition(object):
	def __init__(self,
			path: PathLike, size: Union[int, str], 
			filesystem: str, name: str,
			efi: PathLike=None, boot: PathLike=None):
		"""Object Representing a Partition

		Arguments:
			path: a pathlike object
			size: Size of the partition in bytes
			filesystem: The filesystem for the partition
			name: The Logical Volume name, Root, Boot or ESP
		"""
		self.path = path
		self.size = size
		self.filesystem = filesystem
		self.name = name
		self.efi = efi # Path(str(disk)+'1')
		self.boot = boot # Path(str(disk)+'2')

	def lv_create(self, volume, space_left):
		try:
			print(f"creating logical volume {self.name} with {byte_to_gig_trunc(self.size)} GB")
		except:
			print(f"creating logical volume {self.name} with {byte_to_gig_trunc(space_left)} GB")

		if self.size == '100%FREE':
			shell.lvcreate._n(self.name, '-l', self.size, '--yes', volume)
		else:
			shell.lvcreate._n(self.name, '-L', f'{int(self.size)}b', '--yes', volume)

	def mkfs(self, volume: str=None):
		device = f"/dev/{volume}/{self.name}"
		# Need to change some options if we're running fat
		if self.filesystem == 'fat32':
			option = '-F32'
			filesystem = 'fat'
		else:
			filesystem = self.filesystem
			option = '-F'

		if self.efi:
			device = self.efi
		if self.boot:
			device = self.boot

		print(f"making filesystem: {self.filesystem} on {device}")
		shell(f"mkfs.{filesystem}", option, device)

	def mount(self, volume: str=None):
		device = f"/dev/{volume}/{self.name}"

		if self.efi:
			device = self.efi
		if self.boot:
			device = self.boot

		if self.name == 'root':
			if ROOT_DIR.exists():
				eprint("/target already exists. stopping so we don't ruin anything")
				exit(1)
			ROOT_DIR.mkdir()
			mount_path = ROOT_DIR

		else:
			mount_path = ROOT_DIR / str(self.path).lstrip('/')
			if mount_path.exists():
				eprint(f"{mount_path} already exists. stopping so we don't ruin anything")
				exit(1)
			mount_path.mkdir()

		print(f"mounting {device} to {mount_path}")
		shell.mount(device, mount_path)

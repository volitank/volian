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

from subprocess import run, STDOUT
from sys import stderr, stdout
from utils import byte_to_gig_trunc, ask, get_password, meg_to_byte, gig_to_byte, ask_list
from logger import eprint 
from constant import FILESYSTEMS, EFI, LINUX_BOOT, LINUX_LVM, FSTAB_FILE, FSTAB_HEADER
from typing import TextIO, Union
from pathlib import Path
from time import sleep
from collections import Counter

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
			esp_tuple, space_left = ask_part_size(Path('/boot/efi'), space_left)
			boot_tuple, space_left = ask_part_size(Path('/boot/'), space_left)
			root_tuple, space_left = ask_part_size(Path('/'), space_left)

			# Part list is going to be our list that we use for operations.
			part_list = [esp_tuple, boot_tuple, root_tuple]
			# This list is only for making sure we aren't defining duplicate mount points.
			_path_list = [esp_tuple[0], boot_tuple[0], root_tuple[0]]

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
					new_part, space_left = ask_part_size(path, space_left)

					# Add that new partition to our list.
					part_list.append(new_part)
					part_list.sort
					# Check if they just defined free more than once.
					if str(part_list).count('100%FREE') > 1:
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
					if part_list[n][1] == '100%FREE':
						part_list.append(part_list.pop(n))
				return part_list, disk, space_left

		# Using Ctrl+C will restart the partitioner
		except KeyboardInterrupt:
			print("\nrestarting partitioner..\n")
			# We set a sleep so you can Ctrl+C again to exit the function
			sleep(2)
			continue

def lv_create(part_size: Union[str, int] , name: str, volume: str, logfile: TextIO=None):
	"""Function for making a logical volume.

	Arguments:
		part_size: either 100%FREE or [int | str] number in bytes 
		name: name of the logical volume. 'root' as an example
		volume: name of the volume group the LV will belong too. 'debianvg' as an example
		logfile: expects a file such as file = open('/tmp/logfile', 'w')
	"""
	commands = ["lvcreate", "-n", f"{name}"]
	if part_size == '100%FREE':
		commands.extend(["-l", f"{part_size}"])
	else:
		commands.extend(["-L", f"{part_size}b"])

	commands.append(f"{volume}")
	if logfile is None:
		run(commands, stdout=stderr, stderr=stdout).check_returncode()
	else:
		run(commands, stdout=logfile.open('a'), stderr=logfile.open('a')).check_returncode()

def choose_disk():
	'Asks user for block device. Returns Path object'
	# There may be a better way of getting disks that are applicable but for now this works.
	data = run(["lsblk", "-pro", "NAME,TYPE,SIZE,MOUNTPOINT"], capture_output=True).stdout.decode().strip().split('\n')
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

def ask_part_size(part_path: str, size: int):
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
			# We don't need boot or efi, they aren't going to be lvm
			if str(part_path) != '/boot/efi' and str(part_path) != '/boot':
				# Let us name root appropriately 
				if str(part_path) == '/':
					lv_name = 'root'
				# Everything else will be named according to their path minus the first slash
				# All remaining slashes will be replaced with an underscore '/srv/volian' becomes 'srv_volian'
				else:
					lv_name = str(part_path).lstrip('/').replace('/', '_')
			else:
				lv_name = False

			if str(part_path) == '/boot/efi':
				filesystem = 'fat32'
			else:
				filesystem = ask_list(FILESYSTEMS, 'filesystem')

			part_tupe = (part_path, part_size, filesystem, lv_name)
			try:
				return part_tupe, (size - part_size)
			except TypeError:
				return part_tupe, size

		except ValueError:
			eprint(f"that isn't a valid number")

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
		path, size, fs, lv_name = part
		# If the size is free change it to remaining space
		if size == '100%FREE':
			size = space_left
		# Print our parts with our column width
		print(
			str(path).ljust(col_width),
			str(fs).ljust(col_width),
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

	for part in part_list:
		path, size, fs, lv_name = part
		if str(path) == '/':
			iter_tupe = (f"/dev/mapper/{volume}-{lv_name}",str(path),fs,"errors=remount-ro","0","1")
		elif str(path) == '/boot':
			iter_tupe = (f"UUID={boot_uuid}",str(path),fs,"defaults","0","2")
		elif str(path) == '/boot/efi':
			iter_tupe = (f"UUID={efi_uuid}",str(path),"vfat","umask=0077","0","1")
		else:
			iter_tupe = (f"/dev/mapper/{volume}-{lv_name}",str(path),fs,"defaults","0","2")
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

		# After our header is written we need our sub_header
		device, mount, fs, options, dump, _pass = fstab_list.pop(0)
		print(
		str(device).ljust(device_width),
		str(mount).ljust(mount_width),
		str(fs).ljust(8),
		str(options).ljust(options_width),
		str(dump).ljust(8),
		str(_pass).ljust(2),
		file=fstab_file
		)

		# efi, boot and root are always the first 3 entries in that order.
		# We have to have root as the first entry.
		device, mount, fs, options, dump, _pass = fstab_list.pop(2)
		print(
		str(device).ljust(device_width),
		str(mount).ljust(mount_width),
		str(fs).ljust(8),
		str(options).ljust(options_width),
		str(dump).ljust(8),
		str(_pass).ljust(2),
		file=fstab_file
		)

		# Now we need to make sure we put our boot entry in there next
		device, mount, fs, options, dump, _pass = fstab_list.pop(1)
		print(
		str(device).ljust(device_width),
		str(mount).ljust(mount_width),
		str(fs).ljust(8),
		str(options).ljust(options_width),
		str(dump).ljust(8),
		str(_pass).ljust(2),
		file=fstab_file
		)

		# Now we can iterate normally
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

def luks_format(device: str, luks_name: str, logfile: TextIO=None):
	"""Function for encrypting a block device.

	Arguments:
		device: should be a block device as /dev/sdb2 or /dev/mapper/vg_name-lv_name
		luks_name: what to name the container. 'root_crypt'
		logfile: expects a file such as file = open('/tmp/logfile', 'w')
	"""
	# Create luks container
	# Possible these should be separate functions
	luks_pass = get_password()

	luksFormat = ["cryptsetup", "luksFormat", "--hash=sha512", "--key-size=512", device]
	luksOpen = ["cryptsetup", "open", device, luks_name]

	print("formatting your luks volume..")
	if logfile is None:
		run(luksFormat, text=True, input=luks_pass).check_returncode()
	else:
		run(luksFormat, text=True, input=luks_pass, stdout=logfile.open('a'), stderr=STDOUT).check_returncode()

	print("opening luks volume..")
	if logfile is None:
		run(luksOpen, text=True, input=luks_pass).check_returncode()
	else:
		run(luksOpen, text=True, input=luks_pass, stdout=logfile.open('a'), stderr=STDOUT).check_returncode()
	del luks_pass

def mkfs(device: str, filesystem: str, logfile: TextIO=None):
	"""Function for making a filesystem.

	Arguments:
		device: should be a block device as /dev/sdb2 or /dev/mapper/vg_name-lv_name
		filesystem: fat32, ext2, ext4 etc
		logfile: expects a file such as file = open('/tmp/logfile', 'w')
	"""

	if filesystem == 'fat32':
		option = '-F32'
		filesystem = 'fat'
	else:
		option = '-F'

	commands = ["echo", f"mkfs.{filesystem}", f"{option}", f"{device}"]

	print(f'creating {filesystem} on {device}')
	if logfile is None:
		run(commands).check_returncode()
	else:
		run(commands, stdout=logfile.open('a'), stderr=STDOUT).check_returncode()

def mount(device: str, target: str,*args: str, logfile: TextIO=None):
	"""Function for mounting a filesystem.

	Arguments:
		device: should be a block device as /dev/sdb2 or /dev/mapper/vg_name-lv_name
		target: target path to mount the device such as /boot/efi
		logfile: expects a file such as file = open('/tmp/logfile', 'w')
		args: any extra options you might want to pass.

	example to mount readonly::

	mount('/dev/sda1', '/mnt/storage', '--options', 'ro')
	"""
	commands = ["mount"]
	for arg in args:
		commands.append(arg)
	commands.extend([device, target])

	if logfile is None:
		run(commands).check_returncode()
	else:
		run(commands, stdout=logfile.open('a'), stderr=STDOUT).check_returncode()

def sfdisk(part_list: list, disk: str, logfile: TextIO=None):

	for part in part_list:
		path, size, fs, lv_name = part
		if str(path) == '/boot/efi':
			esp_size = size
		if str(path) == '/boot':
			boot_size = size

	commands = ['sfdisk', '--quiet', '--label', 'gpt', str(disk)]

	parts = (
		# Format is <start>,<size>,<type>\n to separate entries
		f",{esp_size},{EFI}\n"
		+f",{boot_size},{LINUX_BOOT}\n"
		+f",,{LINUX_LVM}"
		)

	if logfile is None:
		run(commands, text=True, input=parts).check_returncode()
	else:
		run(commands, text=True, input=parts, stdout=logfile.open('a'), stderr=STDOUT).check_returncode()
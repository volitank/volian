from argparse import FileType
from subprocess import DEVNULL, run, STDOUT
from sys import stderr, stdin, stdout
from func import byte_to_gig_trunc, ask, get_password, meg_to_byte, gig_to_byte
from logger import wprint, eprint 
from constant import ESP_SIZE_M, BOOT_SIZE_M, VOLIAN_LOG
from typing import TextIO, Union
from pathlib import Path

def lv_create(part_size: Union[str, int] , name: str, volume: str, logfile: TextIO=None):
	"""Function for making a logical volume.

	Arguments:
		part_size: either 100%FREE or [int | str] number in bytes 
		name: name of the logical volume. 'root' as an example
		volume: name of the volume group the LV will belong too. 'debianvg' as an example
		logfile: expects a file such as file = open('/tmp/logfile', 'w')
	"""
	commands = ["echo", "lvcreate", "-n", f"{name}"]
	if part_size == '100%FREE':
		commands.extend(["-l", f"{part_size}"])
	else:
		commands.extend(["-L", f"{part_size}b"])

	commands.append(f"{volume}")
	if logfile is None:
		run(commands, stdout=stderr, stderr=stdout).check_returncode()
	else:
		run(commands, stdout=logfile.open('a'), stderr=logfile.open('a')).check_returncode()
	return f'/dev/{volume}/{name}'

	print(f'creating ext4 on /dev/{volume}/{name}')
	run(["sudo", "mkfs.ext4", "-F", "-q", f"/dev/{volume}/{name}"]).check_returncode()

def choose_disk():
	run(["lsblk", "--exclude", "7"])
	while True:
		disk = input("Which disk you would like to use? /dev/")
		if Path.exists(f"/dev/{disk}"):
			return disk
		else:
			eprint(f"/dev/{disk} doesn't exist")

def define_part(disk, no_part: bool=False):
	true_size = (float(Path(f"/sys/block/{disk}/size").read_text()) * 512)
	space_left = true_size - (ESP_SIZE_M + BOOT_SIZE_M)
	# We require a value for root
	if no_part:
		root = True
	else:
		root, space_left = ask_part(' ', space_left)

	# Check if the user wants a separate partition for /var
	if ask("\nWould you like /var to be separate? Y/n"):
		if no_part:
			var = True
		else:
			var, space_left = ask_part('var', space_left)
	else:
		var = None

	# Check to see if we want a separate /home
	if ask("\nWould you like /home to be separate? Y/n"):
		if no_part:
			home = True
		else:
			home, space_left = ask_part('home', space_left)
	else:
		home = None

	# Check to see if we want a separate /usr
	if ask("\nWould you like /usr to be separate? Y/n"):
		if no_part:
			usr = True
		else:
			usr, space_left = ask_part('usr', space_left)
	else:
		usr = None
	return root, home, var, usr

def filter_input(unknown):
	'convert input to byte from meg or gig'
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

def ask_part_size(part_name: str, size: int, root=False):
	"""Function for determining if, and what size parts to make

	Arguments:
		part_name: should be simple name of part such as 'root' or 'home'
		size: free space left on the block device as an integer in bytes
		root: if True skip the ask to be separate. Must configure root!
	"""
	while True:
		if not root:
			# If it's not the root partition then ask if they would like it separate.
			# If they don't want it separate we need to return None and then the size passed through so it stays the same
			if not ask(f"\nWould you like /{part_name} to be separate? Y/n"):
				return None, size
		try:
			human = byte_to_gig_trunc(size)
			# Make the size human readable. and then ask them how big they want the partition. 
			human_part_size = input(f"\n{human} GB of disk space remains\nHow much space would you like to allocate to /{part_name}? [512M, 10G, free] ")
			# If we decide to support non LVM situations we will probably need to do something about this
			if human_part_size in ['free', 'Free']:
				return '100%FREE', size
			# Figure out if they gave us Megabyte or Gigabyte and then convert it to byte
			if filter_input(human_part_size):
				part_size = filter_input(human_part_size)
				if part_size > size:
					eprint(f"{human_part_size} GB is more than you have left.. try again")
				else:
					return part_size, (size - part_size)
		except ValueError:
			eprint(f"that isn't a valid number")

def write_fstab():
	pass

def luks_format(disk, luks_name):
	# Create luks container
	luks_pass = get_password()
	print("formatting your luks volume..")
	run(["sudo", "cryptsetup", "luksFormat", "--hash=sha512", "--key-size=512", f"/dev/{disk}3"], text=True, input=luks_pass).check_returncode()
	print("opening luks volume..")
	run(["sudo", "cryptsetup", "open", f"/dev/{disk}3", f"{luks_name}"], text=True, input=luks_pass).check_returncode()
	del luks_pass

def mkfs(device: str, filesystem: str, logfile: TextIO=None):
	"""Function for making a filesystem.

	Arguments:
		device: should be a block device as /dev/sdb2 or /dev/mapper/vg_name-lv_name
		filesystem: fat, ext2, ext4
		logfile: expects a file such as file = open('/tmp/logfile', 'w')
	"""

	if filesystem == 'fat':
		option = '-F32'
	else:
		option = '-F'

	commands = ["echo", f"mkfs.{filesystem}", f"{option}", f"{device}"]

	print(f'creating {filesystem} on {device}')
	if logfile is None:
		run(commands, stdout=stderr, stderr=stdout).check_returncode()
	else:
		run(commands, stdout=logfile.open('a'), stderr=logfile.open('a')).check_returncode()

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

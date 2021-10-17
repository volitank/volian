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

from subprocess import run
from os.path import exists
import logging
from const import ESP_SIZE_M, BOOT_SIZE_M, MIRROR_LIST
from math import trunc
from pathlib import Path
from getpass import getpass

eprint = logging.error
vprint = logging.info
wprint = logging.warning

def choose_disk():
	run(["lsblk", "--exclude", "7"])
	while True:
		disk = input("Which disk you would like to use? /dev/")
		if exists(f"/dev/{disk}"):
			return disk
			break
		else:
			eprint(f"/dev/{disk} doesn't exist")

def ask(question):
	"""resp = input(f'{question}? [Y/n]

	Y returns True
	N returns False
	"""
	while True:
		resp = input(f'{question}? [Y/n]')
		if resp in ['y', 'Y']:
			return True
		elif resp in ['n', 'N']:
			return False
		else:
			eprint("Not a valid choice kiddo")

def byte_to_gig_trunc(byte: int):
	"Do not use this for calulations. This is only for displaying pretty for the user."
	gb = byte /1024**3
	fixing = trunc(gb *100)
	human = fixing /100
	return human

def gig_to_byte(gb: int):
	byte = gb *1024**3
	return byte

def meg_to_byte(mb: int):
	byte = mb *1024**2
	return byte

def byte_to_sector(byte: int):
	sector = byte / 512
	return sector

def filter_input(unknown):
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

def ask_part(part, size):

	while True:
		try:
			human = byte_to_gig_trunc(size)
			human_part_size = input(f"\n{human} GB of disk space remains\nHow much space would you like to allocate to /{part}? [512M, 10G, free] ")
			if human_part_size in ['free', 'Free']:
				return '100%FREE', size
			if filter_input(human_part_size):
				part_size = filter_input(human_part_size)
				if part_size > size:
					wprint(f"{human_part_size} GB is more than you have left.. try again")
				else:
					return part_size, (size - part_size)
		except ValueError:
			wprint(f"that isn't a valid number")

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

def print_layout(root, home, var, usr):

	print("\nDisk layout:")
	print(f"/efi \t\t{byte_to_gig_trunc(ESP_SIZE_M)} GB")
	print(f"/boot/efi \t{byte_to_gig_trunc(BOOT_SIZE_M)} GB")
	if root == '100%FREE':
		print(f"/ \t\t{root}")
	else:	
		print(f"/ \t\t{byte_to_gig_trunc(root)} GB")

	if home != None:
		if home == '100%FREE':
			print(f"/home \t\t{home}")
		else:
			print(f"/home \t\t{byte_to_gig_trunc(home)} GB")

	if var != None:
		if var == '100%FREE':
			print(f"/var \t\t{var}")
		else:
			print(f"/var \t\t{byte_to_gig_trunc(var)} GB")

	if usr != None:
		if usr == '100%FREE':
			print(f"/usr \t\t{usr}")
		else:
			print(f"/usr \t\t{byte_to_gig_trunc(usr)} GB")

def get_password():
	"Asks user for password, confirms it and returns it"
	while True:
		password = getpass("password:")
		confirmpass = getpass("confirm password:")
		if password == confirmpass:
			vprint("passwords match")
			return password
		del password
		eprint("passwords don't match! try again.")

def lv_create(part, name, volume):
	if part != '100%FREE':
		print(f'creating logical volume "{name}" with {byte_to_gig_trunc(part)} GB')
		run(["sudo", "lvcreate", "-n", f"{name}", "-L", f"{part}b", f"{volume}"]).check_returncode()
	else:
		print(f'creating logical volume "{name}" with the rest of your free space')
		run(["sudo", "lvcreate", "-n", f"{name}", "-l", f"{part}", f"{volume}"]).check_returncode()
	print(f'creating ext4 on /dev/{volume}/{name}')
	run(["sudo", "mkfs.ext4", "-F", "-q", f"/dev/{volume}/{name}"]).check_returncode()

def mirror_url():
	while True:
		sum = -1
		for mirror in MIRROR_LIST:
			sum = sum +1
			print(f"{sum} {mirror}")
		resp = int(input("please select the number of the mirror you would like to use: "))
		if resp in range(0, 30):
			url = MIRROR_LIST[resp]
			return url
		else:
			print("That choice wasn't on the list.")

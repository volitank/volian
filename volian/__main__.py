#!/usr/bin/env python3

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
# GNU General Public License for more details.tures

# You should have received a copy of the GNU General Public License
# along with volian.  If not, see <https://www.gnu.org/licenses/>.

import argparse
from sys import stderr, argv
from subprocess import run, PIPE, DEVNULL
from os import mkdir
from pathlib import Path
from shutil import copy, move
from platform import machine
from pydoc import pager
from argparse import SUPPRESS
from constant import (	APT_SOURCES, BACKUP_BASHRC, BOOT_DIR, VOLIAN_LOG, EFI, EFI_DIR, ESP_SIZE_M, BOOT_SIZE_M, EFI,
								FSTAB_FILE, HOME_DIR, HOSTNAME_FILE, HOSTS_FILE, LINUX_BOOT, LINUX_LVM, RELEASE_OPTIONS, 
								VIM_DEFAULT, VOLIAN_BASHRC, VOLIAN_VIM, ROOT_BASHRC, USER_BASHRC,
								LOCALE_FILE, ROOT_DIR, USR_DIR, VAR_DIR, LICENSE
								)

from mirror import choose_mirror, get_country_list, get_url_list, ask_list, parse_mirror_master
from func import ask, choose_disk, define_part, print_layout, get_password
from logger import eprint, vprint, wprint
from partition import luks_format, mount, lv_create

# Custom Parser for printing help on error.
class volianParser(argparse.ArgumentParser):
	def error(self, message):
		stderr.write('error: %s\n' % message)
		self.print_help()
		exit(1) 

# Custom Action for --release-options switch
class releaseOptions(argparse.Action):
	def __init__(self,
			option_strings,
			dest=SUPPRESS,
			default=SUPPRESS,
			help="show release options and exit"):
		super(releaseOptions, self).__init__(
			option_strings=option_strings,
			dest=dest,
			default=default,
			nargs=0,
			help=help)
	def __call__(self, parser, args, values, option_string=None):
		#setattr(args, self.dest, values)
		print(RELEASE_OPTIONS)
		parser.exit()

# Custom Action for --license switch
class GPLv3(argparse.Action):
	def __init__(self,
			option_strings,
			dest=SUPPRESS,
			default=SUPPRESS,
			help='reads the GPLv3'):
		super(GPLv3, self).__init__(
			option_strings=option_strings,
			dest=dest,
			default=default,
			nargs=0,
			help=help)
	def __call__(self, parser, args, values, option_string=None):
		#setattr(args, self.dest, values)
		with open(LICENSE, 'r') as file:
			pager(file.read())
		parser.exit()

def main():

	formatter = lambda prog: argparse.HelpFormatter(prog,
													max_help_position=64)
	bin_name = Path(argv[0]).name
	version = 'v0.01'
	parser = volianParser(	formatter_class=formatter,
							usage=f'{bin_name} <distro> [--options]'
							)

	parser.add_argument('distro', choices=['ubuntu', 'debian'], metavar='<debian|ubuntu>')
	parser.add_argument('--release', nargs='?', metavar='release', help='choose your distro release. stable is default for Debian. latest LTS for Ubuntu')
	parser.add_argument('--no-part', action="store_true", help="using this switch will skip partitioning")
	parser.add_argument('--minimal', action='store_true', help="uses the variant=minbase on the backend of debootstrap. Only use this if you're sure you want it")
	parser.add_argument('--version', action='version', version=f'{bin_name} {version}')
	parser.add_argument('--release-options', action=releaseOptions)
	parser.add_argument('--license', action=GPLv3)

	argument = parser.parse_args()
	distro = argument.distro
	no_part = argument.no_part
	release = argument.release

	# Define if we want to create an fstab
	fstab = True
	
	# For now, by default our vg-group name will be the distro
	# I have plans on making these configurable, but a lot in front of me right now
	volume = distro
	luks_name='root_crypt'

	# Lets do a check on our arch
	if machine() == 'x86_64':
		arch = 'amd64'
	else:
		eprint("arch other than amd64 is not supported at the moment")
		exit(1)

	print('welcome to volian installer v.01')
	input('press enter to continue..')

	if not no_part:

		# if --no-part isn't selected then we create our partitions.
		wprint("this installer currently only supports configurations with lvm")
		wprint("You may only use the entire disk")
		wprint("NO mbr, efi only")
		wprint('In the event you want to make your own partitions for installation select "n"')
		wprint("mount your partitions at /target, /target/boot, etc. then run ./installer.py --no-part")
		if not ask("Is that okay"):
			print("this installer isn't good enough for you.. exiting..")
			exit(0)

		while True:
			disk = choose_disk()
			root_size, home_size, var_size, usr_size = define_part(disk)
			if [root_size, home_size, var_size, usr_size].count('100%FREE') < 2:
				print_layout(root_size, home_size, var_size, usr_size)
				if ask("Is this layout okay"):
					# Maybe format things like this
					# root_list = [root_size, 'root']
					break
			else:
				eprint("you can't have 100%free defined twice.")

		# Ask for luks or no
		if ask("do you want to ecrypt your system with luks?"):
			part_name = 'luks'
		else:
			part_name = 'lvm'

		# Create our partitions
		print(f'\ncreating partitions on /dev/{disk}')
		run(['sudo', 'sfdisk', '--quiet', '--label', 'gpt', f"/dev/{disk}"], text=True, input=
			# Format is <start>,<size>,<type>\n to separate entries
			(f",{int(ESP_SIZE_M/512)},{EFI}\n"
			+f",{int(BOOT_SIZE_M/512)},{LINUX_BOOT}\n"
			+f",,{LINUX_LVM}")).check_returncode()

		efi_part = f'/dev/{disk}1'
		boot_part = f'/dev/{disk}2'

		# If we're using luks encryption
		if part_name == 'luks':
			luks_format()
			pv_part = f"/dev/mapper/{luks_name}"
		else:
			pv_part = f"/dev/{disk}3"

		# Create LVM
		print("\ncreating physical volume and volume group")
		run(["sudo", "pvcreate", f"{pv_part}"]).check_returncode()
		run(["sudo", "vgcreate", f"{volume}", f"{pv_part}"]).check_returncode()

		# We need to handle everything that's not free first
		if root_size != '100%FREE':
			lv_create(root_size, 'root', volume)

		if home_size is not None:
			if home_size != '100%FREE':
				lv_create(home_size, 'home', volume)

		if var_size is not None:
			if var_size != '100%FREE':
				lv_create(var_size, 'var', volume)

		if usr_size is not None:
			if usr_size != '100%FREE':
				lv_create(usr_size, 'usr', volume)

		# Now whatever we have that is free can take up the rest of the LVM
		if root_size == '100%FREE':
			lv_create(root_size,'root', volume)

		if home_size == '100%FREE':
			lv_create(home_size, 'home', volume)

		if var_size == '100%FREE':
			lv_create(var_size, 'var', volume)

		if usr_size == '100%FREE':
			lv_create(usr_size, 'usr', volume)

		# Make filesystems
		print("making /boot and /boot/efi filesystems")
		run(["sudo", "mkfs.fat", "-F32", f"/dev/{disk}1"], stdout=DEVNULL, stderr=DEVNULL).check_returncode()
		run(["sudo", "mkfs.ext2", "-F", "-q", f"/dev/{disk}2"]).check_returncode()

		ROOT_DIR = Path('/target')
		if ROOT_DIR.exists():
			eprint("/target already exists. stopping so we don't ruin anything")
			exit(1)
		else:
			ROOT_DIR.mkdir()

		print("mounting volumes")
		mount(f"/dev/{volume}/root", ROOT_DIR, logfile=VOLIAN_LOG)

		BOOT_DIR.mkdir()
		mount(f"/dev/{disk}2", BOOT_DIR, logfile=VOLIAN_LOG)

		EFI_DIR.mkdir()
		mount(f"/dev/{disk}1", EFI_DIR, logfile=VOLIAN_LOG)

		if home_size is not None:
			HOME_DIR.mkdir()
			mount(f"/dev/{volume}/home", HOME_DIR, logfile=VOLIAN_LOG)

		if var_size is not None:
			VAR_DIR.mkdir()
			mount(f"/dev/{volume}/var", VAR_DIR, logfile=VOLIAN_LOG)

		if usr_size is not None:
			USR_DIR.mkdir()
			mount(f"/dev/{volume}/usr", USR_DIR, logfile=VOLIAN_LOG)

	if no_part:
		print("if we don't partition for you it makes it hard to understand what to do")
		print("with this we assume efi is on sdx1 and boot is on sdx2")
		print("lvm is still the only supported method")
		if ask("is all of this okay"):
			print("\nif you want to configure more than /home, /var and /usr separately")
			print("then we will require you to create your own /etc/fstab")
			if ask("should we generate the /etc/fstab for you"):
				disk = choose_disk()
				root, home, var, usr = define_part(disk, no_part=True)
			else:
				fstab = False
		else:
			print("this installer isn't good enough for you.. exiting..")
			exit(0)

	# Now we need to do our installation
	# Handle what direction we go in with debootstrap
	# And also build our sources.list
	if distro == 'debian':
		distro = "debian"
		url = choose_mirror()

		if release is None:
			print("debian release not selected. defaulting to stable")
			release="stable"

		sources_list = (
		"# Installed with https://Project.URL/here\n\n"
		f"deb http://{url}/debian/ {release} main\n"
		f"deb-src http://{url}/debian/ {release} main\n\n"
		)

		sources_nosid = (
		f"deb http://{url}/debian/ {release}-updates main\n"
		f"deb-src http://{url}/debian/ {release}-updates main\n\n"
		f"deb http://{url}/debian-security/ {release}-security main\n"
		f"deb-src http://{url}/debian-security/ {release}-security main")

	elif distro == 'ubuntu':
		distro = "ubuntu"
		url = "us.archive.ubuntu.com"

		if release is None:
			print("ubuntu release not selected. defaulting to hirsute")
			release="hirsute"

		sources_list = (
		"# Installed with https://Project.URL/here\n\n"
		f"deb http://{url}/ubuntu {release} main restricted universe multiverse\n"
		f"deb http://{url}/ubuntu {release}-updates main restricted universe multiverse\n"
		f"deb http://{url}/ubuntu {release}-backports main restricted universe multiverse\n"
		f"deb http://{url}/ubuntu {release}-security main restricted universe multiverse")

	print(f'starting installation of {distro} {release}.. this can take a while..')

	# Start installation
	with open(VOLIAN_LOG, 'wb') as logfile:
		print(f'initial bootstrapping log can be found at {VOLIAN_LOG}')
		if argument.minimal:
			run(["debootstrap", "--variant-minbase", f"{release}", f"{ROOT_DIR}", f"http://{url}/{distro}"], stdout=logfile, stderr=logfile).check_returncode()
		else:
			run(["debootstrap", f"{release}", f"{ROOT_DIR}", f"http://{url}/{distro}"], stdout=logfile, stderr=logfile).check_returncode()
	print('initial bootstrapping complete')

	# Let's write our sources.list
	with open(APT_SOURCES, 'w') as file:
		file.write(sources_list)
		if distro == 'debian' and release != 'sid':
			file.write(sources_nosid)

	if fstab:
		efi_uuid = run(["blkid", f"/dev/{disk}1", "--output", "value"], stdout=PIPE).stdout.decode().split()[0]
		boot_uuid = run(["blkid", f"/dev/{disk}2", "--output", "value"], stdout=PIPE).stdout.decode().split()[0]
		
		# Time to write our fstab
		with open(FSTAB_FILE, 'w') as file:
			tab = '\t'
			fstab_header = (
			"# /etc/fstab: static file system information.\n"
			"#\n"
			"# Use 'blkid' to print the universally unique identifier for a\n"
			"# device; this may be used with UUID= as a more robust way to name devices\n"
			"# that works even if disks are added and removed. See fstab(5).\n"
			"#\n"
			f"# <file system>{tab*7}<mount point>\t<type>\t<options>{tab*4}<dump>\t<pass>\n"
			f"/dev/mapper/{volume}-root{tab*6}/{tab*3}ext4\terrors=remount-ro\t\t0\t\t1\n"
			)

			file.write(fstab_header)
			# We only have one tab here cause UUID is a long boi for boot
			if usr is not None:
				file.write(f"/dev/mapper/{volume}-usr{tab*6}/usr\t\text4\tdefaults{tab*4}0\t\t2\n")
			file.write(f"UUID={boot_uuid}\t/boot\t\text2\tdefaults{tab*4}0\t\t2\n")
			file.write(f"UUID={efi_uuid}{tab*8}/boot/efi\tvfat\tumask=0077{tab*4}0\t\t1\n")
			if home is not None:
				file.write(f"/dev/mapper/{volume}-home{tab*6}/home\t\text4\tdefaults{tab*4}0\t\t2\n")
			if var is not None:
				file.write(f"/dev/mapper/{volume}-var{tab*6}/var\t\text4\tdefaults{tab*4}0\t\t2\n")
			file.write(f"tmpfs{tab*10}/tmp\t\ttmpfs\tmode=1777,nosuid,nodev\t0\t\t0")
			# Maybe we want to give an option for a swapfile not right now tho?
			#"#/swapfile									none		swap	sw						0	0"

	# Let us copy volian customizations
	copy(VOLIAN_BASHRC, ROOT_BASHRC)
	move(USER_BASHRC, BACKUP_BASHRC)
	copy(VOLIAN_BASHRC, USER_BASHRC)
	copy(VOLIAN_VIM, VIM_DEFAULT)

	# Update locale. Will be configurable eventually
	locale = 'en_US.UTF-8 UTF-8\n'
	with open(LOCALE_FILE, 'r') as file:
		locale_data = ''
		for line in file.readlines():
			if locale in line:
				line = locale
			locale_data = locale_data + line
	with open(LOCALE_FILE, 'w') as file:
		file.write(locale_data)

	# Set our hostname. Will make it configurable eventually
	hostname = 'volian\n'
	with open(HOSTNAME_FILE, 'w') as file:
		file.write(hostname)
	# Define basic etc hosts file and write it
	etc_hosts = (
	'#etc/hosts\n'
	'127.0.0.1 localhost\n'
	f'127.0.1.1 {hostname}\n\n'
	'# The following lines are desirable for IPv6 capable hosts\n'
	'::1     ip6-localhost ip6-loopback\n'
	'fe00::0 ip6-localnet\n'
	'ff00::0 ip6-mcastprefix\n'
	'ff02::1 ip6-allnodes\n'
	'ff02::2 ip6-allrouters')

	with open(HOSTS_FILE, 'w') as file:
		file.write(etc_hosts)

## Ask and or create these.
# /etc/network/interfaces, /etc/resolv.conf

## Run These in the chroot when we get there
# apt update
# apt install makedev sudo lvm2 cryptsetup cryptsetup-initramfs grub-efi command-not-found

## NEED TO VERIFY IF NECESSARY
#apt-file update
#update-command-not-found

## Ask user if they would like to install standard packages.
## Encourage them too as things like 
## wget, file, apt-listchanges, xz-utils, bzip2, manpages, bash-completion, openssh-client, lsof, traceroute
## tools you'd expect such as manpages, bash-completion, and ssh won't be available. 
## Are not available without it
# tasksel install standard
# dpkg-reconfigure tzdata
# echo volian > /etc/hostname
#tasksel instal ssh-server
#update-locale LANG=en_US.UTF-8


# # mount none /proc -t proc
# # cd /dev
# # MAKEDEV generic
# or depending on your specific architecture:
# # MAKEDEV std
# # cd ..

# #Maybe do this Idk yet need to walk  through
# mount --bind dev /dev

# # mount -t proc proc /proc
# # mount -t sysfs sysfs /sys

# # Check ls /proc here and if it fails we ned to mount from outside the chroot
# # mount -t proc proc /mnt/ubuntu/proc

if __name__ == "__main__":
	try:
		while True:
			try:
				main()
			except KeyboardInterrupt:
				if ask("\nwould you like to drop to a shell"):
					print("to run the installer again just run type install")
					exit(0)
				print("\nrestarting installer")
	except KeyboardInterrupt:
		print("\nexiting cleanly")
		exit(0)

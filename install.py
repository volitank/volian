#!/usr/bin/env python3

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

import argparse
from sys import stderr, argv
import logging
from subprocess import run, PIPE, DEVNULL
from os.path import exists, basename
from os import mkdir, write
from math import trunc
from pathlib import Path
from getpass import getpass
from shutil import copy, move
from const import MIRROR_LIST, ESP_SIZE_M, BOOT_SIZE_M, EFI, LINUX_BOOT, LINUX_LVM
from platform import machine

from mirror import get_country_list, get_url_list, ask_list, parse_mirror_master
from func import ask, choose_disk, define_part, print_layout, get_password, lv_create

logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO, datefmt='[%Y-%m-%d %H:%M:%S]')

class BinlockParser(argparse.ArgumentParser):
	def error(self, message):
		stderr.write('error: %s\n' % message)
		self.print_help()
		exit(1) 

eprint = logging.error
vprint = logging.info
wprint = logging.warning
def main():

	formatter = lambda prog: argparse.HelpFormatter(prog,
													max_help_position=64)
	bin_name = basename(argv[0])
	parser = BinlockParser(	formatter_class=formatter,
							usage=f'{bin_name} <distro> [--options]'
							)

	parser.add_argument('distro', choices=['ubuntu', 'debian'], metavar='<debian|ubuntu>')
	parser.add_argument('--release', nargs='?', metavar='release', help='choose your distro release. stable is default for Debian. latest LTS for Ubuntu')
	parser.add_argument('--no-part', action="store_true", help="using this switch will skip partitioning")
	parser.add_argument('--minimal', action='store_true', help="uses the variant=minbase on the backend of debootstrap. Only use this if you're sure you want it")
	parser.add_argument('--release-options', action='store_true', help='show --release options and exit')

	argument = parser.parse_args()

	distro = argument.distro
	no_part = argument.no_part
	release = argument.release

	# Define if we want to create an fstab
	fstab = True
	# For now, by default our vggroup name will be the distro
	# I have plans on making these configurable, but a lot in front of me right now
	volume = distro
	luks_name='root_crypt'

	# Lets do a check on our arch
	if machine() == 'x86_64':
		arch = 'amd64'
	else:
		eprint("arch other than amd64 is not supported at the moment")
		exit(1)

	# Logic for our installer debian --release-options
	if argument.release_options is True:
		if distro == 'ubuntu':
			print	("ubuntu:\n"
				"    impish = 22.04 release\n"
				"    hirsute = 21.04 release\n"
				"    focal = 20.04 release"
					)

		if distro == 'debian':
			print	("debian:\n"
				"    sid = unstable branch.\n"
				"    testing = testing branch\n"
				"    bullseye = stable brachh\n"
				"you may also use the alternate names such as unstable and stable"
				)
		exit(0)

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
			root, home, var, usr = define_part(disk)
			if [root, home, var, usr].count('100%FREE') < 2:
				print_layout(root, home, var, usr)
				if ask("Is this layout okay"):
					break
			else:
				eprint("you can't have 100%free defined twice.")

		print(f"\nMaking partitions.. on /dev/{disk}")

		# Ask for luks or no
		if ask("do you want to ecrypt your system with luks?"):
			part_name = 'luks'
			luks_pass = get_password()
		else:
			part_name = 'lvm'

		# Create our partitions
		print(f'\ncreating partitions on /dev/{disk}')
		run(['sudo', 'sfdisk', '--quiet', '--label', 'gpt', f"/dev/{disk}"], text=True, input=	(f",{int(ESP_SIZE_M/512)},{EFI}\n"
																					+f",{int(BOOT_SIZE_M/512)},{LINUX_BOOT}\n"
																					+f",,{LINUX_LVM}")).check_returncode()

		# If we're using luks encryption
		if part_name == 'luks':
			# Create luks container
			print("formatting your luks volume..")
			run(["sudo", "cryptsetup", "luksFormat", "--hash=sha512", "--key-size=512", f"/dev/{disk}3"], text=True, input=luks_pass).check_returncode()
			print("opening luks volume..")
			run(["sudo", "cryptsetup", "open", f"/dev/{disk}3", f"{luks_name}"], text=True, input=luks_pass).check_returncode()
			del luks_pass
			pvdisk = f"/dev/mapper/{luks_name}"
		else:
			pvdisk = f"/dev/{disk}3"

		# Create LVM
		print("\ncreating physical volume and volume group")
		run(["sudo", "pvcreate", f"{pvdisk}"]).check_returncode()
		run(["sudo", "vgcreate", f"{volume}", f"{pvdisk}"]).check_returncode()

		# We need to handle everything that's not free first
		if root != '100%FREE':
			lv_create(root, 'root', volume)

		if home is not None:
			if home != '100%FREE':
				lv_create(home, 'home', volume)

		if var is not None:
			if var != '100%FREE':
				lv_create(var, 'var', volume)

		if usr is not None:
			if usr != '100%FREE':
				lv_create(usr, 'usr', volume)

		# Now whatever we have that is free can take up the rest of the LVM
		if root == '100%FREE':
			lv_create(root,'root', volume)

		if home == '100%FREE':
			lv_create(home, 'home', volume)

		if var == '100%FREE':
			lv_create(var, 'var', volume)

		if usr == '100%FREE':
			lv_create(usr, 'usr', volume)

		# Make filesystems
		print("making /boot and /boot/efi filesystems")
		run(["sudo", "mkfs.fat", "-F32", f"/dev/{disk}1"], stdout=DEVNULL, stderr=DEVNULL).check_returncode()
		run(["sudo", "mkfs.ext2", "-F", "-q", f"/dev/{disk}2"]).check_returncode()

		try:
			mkdir('/target')
		except FileExistsError:
			eprint("/target already exists. stopping so we don't ruin anything")
			exit(1)

		print("mounting volumes")
		run(["sudo", "mount", f"/dev/{volume}/root", "/target"]).check_returncode()
		mkdir('/target/boot')
		run(["sudo", "mount", f"/dev/{disk}2", "/target/boot"]).check_returncode()
		mkdir('/target/boot/efi')
		run(["sudo", "mount", f"/dev/{disk}1", "/target/boot/efi"]).check_returncode()

		if home is not None:
			mkdir('/target/home')
			run(["sudo", "mount", f"/dev/{volume}/home", "/target/home"]).check_returncode()

		if var is not None:
			mkdir('/target/var')
			run(["sudo", "mount", f"/dev/{volume}/var", "/target/var"]).check_returncode()

		if usr is not None:
			mkdir('/target/usr')
			run(["sudo", "mount", f"/dev/{volume}/usr", "/target/usr"]).check_returncode()

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
		url = "deb.debian.org"

		print("for debian we give you the option of choosing your mirror")
		print("the default is 'http://deb.debian.org'")

		if ask("Would you like to choose a different mirror"):
			mirror_list = parse_mirror_master()
			country_list = get_country_list(mirror_list, arch)
			country = ask_list(country_list, 'country')
			url_list = get_url_list(mirror_list, country, arch)
			url = ask_list(url_list, 'mirror')

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
	with open('/tmp/bootstrap.log', 'wb') as logfile:
		print('initial bootstrapping log can be found at /tmp/bootstrap.log')
		if argument.minimal:
			run(["debootstrap", "--variant-minbase", f"{release}", "/target", f"http://{url}/{distro}"], stdout=logfile, stderr=logfile).check_returncode()
		else:
			run(["debootstrap", f"{release}", "/target", f"http://{url}/{distro}"], stdout=logfile, stderr=logfile).check_returncode()
	print('initial bootstrapping complete')

	# Let's write our sources.list
	with open('/target/etc/apt/sources.list', 'w') as file:
		file.write(sources_list)
		if distro == 'debian' and release != 'sid':
			file.write(sources_nosid)

	if fstab:
		efi_uuid = run(["blkid", f"/dev/{disk}1", "--output", "value"], stdout=PIPE).stdout.decode().split()[0]
		boot_uuid = run(["blkid", f"/dev/{disk}2", "--output", "value"], stdout=PIPE).stdout.decode().split()[0]
		
		# Time to write our fstab
		with open('/target/etc/fstab', 'w') as file:
			tab = '\t'
			fstab_file = (
			"# /etc/fstab: static file system information.\n"
			"#\n"
			"# Use 'blkid' to print the universally unique identifier for a\n"
			"# device; this may be used with UUID= as a more robust way to name devices\n"
			"# that works even if disks are added and removed. See fstab(5).\n"
			"#\n"
			f"# <file system>{tab*7}<mount point>\t<type>\t<options>{tab*4}<dump>\t<pass>\n"
			f"/dev/mapper/{volume}-root{tab*6}/{tab*3}ext4\terrors=remount-ro\t\t0\t\t1\n"
			)

			file.write(fstab_file)
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
	copy('/files/.bashrc', '/target/root/.bashrc')
	move('/target/etc/skel/.bashrc', '/target/etc/skel/.bashrc.debian')
	copy('/files/.bashrc', '/target/etc/skel/.bashrc')
	copy('/files/defaults.vim', '/target/usr/share/vim/vim82/defaults.vim')

	# Update locale. Will be configurable eventually
	locale = 'en_US.UTF-8 UTF-8\n'
	with open('/target/etc/locale.gen', 'r') as file:
		locale_data = ''
		for line in file.readlines():
			if locale in line:
				line = locale
			locale_data = locale_data + line
	with open('/target/etc/locale.gen', 'w') as file:
		file.write(locale_data)

	# Set our hostname. Will make it configurable eventually
	hostname = 'volian\n'
	with open('/etc/hostname', 'w') as file:
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

	with open('/etc/hosts', 'w') as file:
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

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




from subprocess import run, PIPE, STDOUT
from shutil import copy, move
from platform import machine
from pathlib import Path

from options import arg_parse
from mirror import choose_mirror
from logger import eprint, wprint
from utils import ask, byte_to_gig_trunc
from netcfg import initial_network_configuration, write_interface_file
from partition import define_partitions, luks_format, mount, lv_create, sfdisk, mkfs, write_fstab
from constant import (	APT_SOURCES, BACKUP_BASHRC, BOOT_DIR, RESOLV_CONF, TARGET_RESOLV_CONF, VOLIAN_LOG, EFI_DIR, EFI,
						HOSTNAME_FILE, HOSTS_FILE, VIM_DEFAULT, VOLIAN_BASHRC, VOLIAN_VIM, ROOT_BASHRC, USER_BASHRC,
						LOCALE_FILE, ROOT_DIR
						)

def main():

	parser = arg_parse()
	argument = parser.parse_args()
	distro = argument.distro
	release = argument.release
	
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

	# if --no-part isn't selected then we create our partitions.
	wprint("this installer currently only supports configurations with lvm")
	wprint("you may only use the entire disk")
	wprint("NO mbr, efi only")
	if not ask("Is that okay"):
		print("this installer isn't good enough for you.. exiting..")
		exit(0)


	# # Example of what a network tupel will look like
	# # ip, subnet, gateway, domain, search, nameserver, interface
	# network_tuple = ('10.0.1.20', '/24', '10.0.1.1', 'volitank.com', 'volitank.com', '10.0.1.1', 'ens18')
	network_tuple = initial_network_configuration()

	# # Example of what a partition_list will look like
	# part_list = [	(Path('/boot/efi'), 536870912, 'fat32', None), (Path('/boot'), 1610612736, 'ext2', None),
	# 				(Path('/'), 21474836480, 'ext4', 'root'), (Path('/var'), 21474836480, 'ext4', 'var'),
	# 				(Path('/srv/volicloud'), 21474836480, 'ext4', 'srv_volicloud'), (Path('/home'), '100%FREE', 'ext4', 'home')]
	part_list, disk, space_left = define_partitions()

	# Create our partitions
	print(f'\ncreating partitions on {disk}')
	sfdisk(part_list, disk, VOLIAN_LOG)

	# Ask if we'll be encrypting, then format luks if we are.
	if ask("do you want to ecrypt your system with luks"):
		luks_format()
		pv_part = Path(f"/dev/mapper/{luks_name}")
	else:
		# Our pysical volume will be /dev/sdx3
		pv_part = Path(str(disk)+'3')

	# Create LVM
	print("\ncreating physical volume and volume group")
	# Create our physical volume on either our disk or luks container
	with VOLIAN_LOG.open('a') as logfile:
		run(["pvcreate", f"{pv_part}"], stdout=logfile, stderr=STDOUT).check_returncode()
		# Create the volume group using the distro name as the vg name
		run(["vgcreate", f"{volume}", f"{pv_part}"], stdout=logfile, stderr=STDOUT).check_returncode()

	# Now time to create our Logical Volumes from our part_list
	for part in part_list:
		path, lv_size, fs, lv_name = part
		# We don't need boot or efi, they aren't going to be lvm
		if str(path) != '/boot/efi' and str(path) != '/boot':
			try:
				print(f"creating logical volume {lv_name} with {byte_to_gig_trunc(lv_size)} GB")
			except:
				print(f"creating logical volume {lv_name} with {byte_to_gig_trunc(space_left)} GB")

			lv_create(lv_size, lv_name, volume, logfile=VOLIAN_LOG)
			print(f"making filesystem: {fs} on /dev/{volume}/{lv_name}")
			mkfs(f"/dev/{volume}/{lv_name}", fs, logfile=VOLIAN_LOG)
			# Time to start mounting. We need to check for root because we have to handle it a bit differently
			# We're going to check if the mount point already exists, in reality it shouldn't.
			if str(path) == '/':
				if ROOT_DIR.exists():
					eprint("/target already exists. stopping so we don't ruin anything")
					exit(1)
				ROOT_DIR.mkdir()
				mount_path = ROOT_DIR
			else:
				mount_path = ROOT_DIR / str(path).lstrip('/')
				if mount_path.exists():
					eprint(f"{mount_path} already exists. stopping so we don't ruin anything")
					exit(1)
				mount_path.mkdir()
			print(f"mounting /dev/{volume}/{lv_name} to {mount_path}")
			mount(f"/dev/{volume}/{lv_name}", mount_path, logfile=VOLIAN_LOG)

	# Now that root and everything has been mounted we can do the boot and efi
	print("making /boot and /boot/efi filesystems")
	efi_part = Path(str(disk)+'1')
	boot_part = Path(str(disk)+'2')

	mkfs(efi_part, 'fat32', VOLIAN_LOG)
	# part_list[1][2] should always be the fs we chose
	mkfs(boot_part, part_list[1][2], VOLIAN_LOG)

	print("mounting /boot and /boot/efi filesystems")
	BOOT_DIR.mkdir()
	mount(boot_part, BOOT_DIR, logfile=VOLIAN_LOG)

	EFI_DIR.mkdir()
	mount(efi_part, EFI_DIR, logfile=VOLIAN_LOG)

	# Now we need to do our installation
	# Handle what direction we go in with debootstrap
	# And also build our sources.list
	if distro == 'debian':
		distro = "debian"
		url = choose_mirror(arch)

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
			run(["debootstrap", "--variant-minbase", f"{release}", f"{ROOT_DIR}", f"http://{url}/{distro}"], stdout=logfile, stderr=STDOUT).check_returncode()
		else:
			run(["debootstrap", f"{release}", f"{ROOT_DIR}", f"http://{url}/{distro}"], stdout=logfile, stderr=STDOUT).check_returncode()
	print('initial bootstrapping complete')

	# Let's write our sources.list
	with open(APT_SOURCES, 'w') as file:
		file.write(sources_list)
		if distro == 'debian':
			if release != 'sid' and release != 'unstable':
				file.write(sources_nosid)

	efi_uuid = run(["blkid", efi_part, "--output", "value"], stdout=PIPE).stdout.decode().split()[0]
	boot_uuid = run(["blkid", boot_part, "--output", "value"], stdout=PIPE).stdout.decode().split()[0]
	
	write_fstab(boot_uuid, efi_uuid, volume, part_list)

	# Let us copy volian customizations
	copy(VOLIAN_BASHRC, ROOT_BASHRC)
	move(USER_BASHRC, BACKUP_BASHRC)
	copy(VOLIAN_BASHRC, USER_BASHRC)
	copy(VOLIAN_VIM, VIM_DEFAULT)

	exit()
	# We need to install tasksel standard through the chroot before we do this.
	# Put an exit statement here for now until I can do more testing.
	# But this is well on it's way

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

	# Copy installer resolve.conf
	copy(RESOLV_CONF, TARGET_RESOLV_CONF)

	# Generate configuration file. 
	write_interface_file(network_tuple)

	print('Everything is finished and you should now be able to chroot')
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

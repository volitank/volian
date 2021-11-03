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

from shutil import copy, move
from platform import machine
from pathlib import Path

from options import arg_parse
from mirror import choose_mirror
from logger import eprint, wprint
from partition import define_partitions, write_fstab
from utils import ask, get_password, shell, DEFAULT
from netcfg import initial_network_configuration, write_interface_file
from constant import (	APT_SOURCES, BACKUP_BASHRC, RESOLV_CONF, TARGET_RESOLV_CONF, VOLIAN_LOG, EFI,
						HOSTNAME_FILE, HOSTS_FILE, VIM_DEFAULT, VOLIAN_BASHRC, VOLIAN_VIM, ROOT_BASHRC, USER_BASHRC,
						LOCALE_FILE, ROOT_DIR, LINUX_BOOT, LINUX_LVM
						)

def main():

	parser = arg_parse()
	argument = parser.parse_args()
	distro = argument.distro
	release = argument.release

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

	# Returns a Partition object. Class is defined in partition.py
	part_list, disk, space_left = define_partitions()

	# Create our partitions
	print(f'\ncreating partitions on {disk}')
	for partition in part_list:
		# We have to convert the bytes to sectors
		if partition.name == 'boot_efi':
			esp_size = int(partition.size / 512)
		if partition.name == 'boot':
			boot_size = int(partition.size /512)

	parts = (
	# Format is <start>,<size>,<type>\n to separate entries
	f",{esp_size},{EFI}\n"
	+f",{boot_size},{LINUX_BOOT}\n"
	+f",,{LINUX_LVM}"
	)

	# Who ever wrote pyshell is a genius!
	shell.sfdisk.__quiet.__label.gpt(disk, input=parts)

	# Ask if we'll be encrypting, then format luks if we are.
	if ask("do you want to ecrypt your system with luks"):
		luks_pass = get_password()
		luks_disk = Path(str(disk)+'3')
		print("formatting your luks volume..")
		shell.cryptsetup.luksFormat("--hash=sha512", "--key-size=512", luks_disk, input=luks_pass)

		print("opening luks volume..")
		shell.cryptsetup.open(luks_disk, luks_name, luks_pass)

		del luks_pass

		pv_part = Path(f"/dev/mapper/{luks_name}")
	else:
		# Our pysical volume will be /dev/sdx3
		pv_part = Path(str(disk)+'3')

	# Create LVM
	print("\ncreating physical volume and volume group")
	# Create our physical volume on either our disk or luks container
	shell.pvcreate(pv_part)
	shell.vgcreate(volume, pv_part)

	# Now time to create our Logical Volumes from our part_list
	for partition in part_list:
		# We don't need boot or efi, they aren't going to be lvm
		if partition.name != 'boot_efi' and partition.name != 'boot':
			partition.lv_create(volume, space_left)
			partition.mkfs(volume)
			partition.mount(volume)

	# Now that root and everything has been mounted we can do the boot and efi
	print("making /boot and /boot/efi filesystems")

	for partition in part_list:
		if partition.name == 'boot':
			partition.mkfs()
			partition.mount()

	# We have to iterate this separately becuase boot has to be mounted before /boot/efi
	for partition in part_list:
		if partition.name == 'boot_efi':
			partition.mkfs()
			partition.mount()

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
		"# Installed with https://github.com/volitank/volian\n\n"
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
		"# Installed with https://github.com/volitank/volian\n\n"
		f"deb http://{url}/ubuntu {release} main restricted universe multiverse\n"
		f"deb http://{url}/ubuntu {release}-updates main restricted universe multiverse\n"
		f"deb http://{url}/ubuntu {release}-backports main restricted universe multiverse\n"
		f"deb http://{url}/ubuntu {release}-security main restricted universe multiverse")

	print(f'starting installation of {distro} {release}.. this can take a while..')

	# Start installation
	print(f'initial bootstrapping log can be found at {VOLIAN_LOG}')
	if argument.minimal:
		shell.debootstrap.__variant_minbase(release, ROOT_DIR, f"http://{url}/{distro}")
	else:
		shell.debootstrap(release, ROOT_DIR, f"http://{url}/{distro}")
	print('initial bootstrapping complete')

	# Let's write our sources.list
	with open(APT_SOURCES, 'w') as file:
		file.write(sources_list)
		if distro == 'debian':
			if release != 'sid' and release != 'unstable':
				file.write(sources_nosid)

	efi_uuid = shell.blkid(Path(str(disk)+'1'), "--output", "value", logfile=DEFAULT, capture_output=True).stdout.decode().split()[0]
	boot_uuid= shell.blkid(Path(str(disk)+'2'), "--output", "value", logfile=DEFAULT, capture_output=True).stdout.decode().split()[0]
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

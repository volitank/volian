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
	print("constant isn't intended to be run directly.. exiting")
	exit(1)

from pathlib import Path
# Convert our paths into pathlib objects

ESP_SIZE_M = 536870912 # 512M
BOOT_SIZE_M = 1610612736 # 1.5G

EFI = 'C12A7328-F81F-11D2-BA4B-00A0C93EC93B'
LINUX_BOOT = 'BC13C2FF-59E6-4262-A352-B275FD6F7172'
LINUX_LVM =  'E6D6D379-F507-44C2-A23C-238F2A3DF928'
LINUX_FILESYSTEM = '0FC63DAF-8483-4772-8E79-3D69D8477DE4'
DEBIAN_ORG = 'deb.debian.org'

## Define file constants
# Relative files
here = Path(__file__).parent.resolve()
files = here / 'files'
LICENSE = files / 'LICENSE'
VOLIAN_BASHRC = files / '.bashrc'
VOLIAN_VIM = files / 'defaults.vim'
MIRROR_MASTER = here / 'Mirrors.masterlist'

# Host Files
INTERFACES_FILE = Path('/etc/network/interfaces')
RESOLV_CONF = Path('/etc/resolv.conf')
VOLIAN_LOG = Path('/tmp/volian.log')

# Target files
LOCALE_FILE = Path('/target/etc/locale.gen')
ROOT_BASHRC = Path('/target/root/.bashrc')
USER_BASHRC = Path('/target/etc/skel/.bashrc')
BACKUP_BASHRC = Path('/target/etc/skel/.bashrc.default')
VIM_DEFAULT = Path('/target/usr/share/vim/vim82/defaults.vim')
APT_SOURCES = Path('/target/etc/apt/sources.list')
HOSTS_FILE = Path('/target/etc/hosts')
HOSTNAME_FILE = Path('/target/etc/hostname')
TARGET_RESOLV_CONF = Path('/target/etc/resolv.conf')
INTERFACES_FILE = Path('/target/etc/network/interfaces')
FSTAB_FILE = Path('/target/etc/fstab')

# Define chroot constants
ROOT_DIR = Path('/target')
BOOT_DIR = Path('/target/boot')
EFI_DIR = Path('/target/boot/efi')

#BLOCK_DEV = ['hd', 'sd', 'vd', 'md', 'ad', 'nb', 'ftl', 'pd', 'pf', 'mmc']
FILESYSTEMS = ['ext4', 'ext2', 'fat32', 'xfs', 'btrfs', 'ext3', 'ntfs', 'hfs']

SUBNET_MASK_DICT = {
"255.0.0.0": "/8",
"255.128.0.0": "/9",
"255.192.0.0": "/10",
"255.224.0.0": "/11",
"255.240.0.0": "/12",
"255.248.0.0": "/13",
"255.252.0.0": "/14",
"255.254.0.0": "/15",
"255.255.0.0": "/16",
"255.255.128.0": "/17",
"255.255.192.0": "/18",
"255.255.224.0": "/19",
"255.255.240.0": "/20",
"255.255.248.0": "/21",
"255.255.252.0": "/22",
"255.255.254.0": "/23",
"255.255.255.0": "/24",
"255.255.255.128": "/25",
"255.255.255.192": "/26",
"255.255.255.224": "/27",
"255.255.255.240": "/28",
"255.255.255.248": "/29",
"255.255.255.252": "/30"
}

RELEASE_OPTIONS = (
"usage: volian debian --release sid\n"
"usage: volian ubuntu --release impish\n"
"\nubuntu:\n"
"    impish = 22.04 release\n"
"    hirsute = 21.04 release\n"
"    focal = 20.04 release\n"
"\ndebian:\n"
"    sid = unstable branch.\n"
"    testing = testing branch\n"
"    bullseye = stable branch\n"
"you may also use the alternate names such as unstable and stable"
			)

FSTAB_HEADER = (
"# /etc/fstab: static file system information.\n"
"#\n"
"# Use 'blkid' to print the universally unique identifier for a\n"
"# device; this may be used with UUID= as a more robust way to name devices\n"
"# that works even if disks are added and removed. See fstab(5).\n"
"#\n"
)

INTERFACE_HEADER = (
"# This file describes the network interfaces available on your system\n"
"# and how to activate them. For more information, see interfaces(5).\n"
"\nsource /etc/network/interfaces.d/*\n")
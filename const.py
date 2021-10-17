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

ESP_SIZE_M = 536870912 # 512M
BOOT_SIZE_M = 1610612736 # 1.5G

EFI = 'C12A7328-F81F-11D2-BA4B-00A0C93EC93B'
LINUX_BOOT = 'BC13C2FF-59E6-4262-A352-B275FD6F7172'
LINUX_LVM = 'E6D6D379-F507-44C2-A23C-238F2A3DF928'
LINUX_FILESYSTEM = '0FC63DAF-8483-4772-8E79-3D69D8477DE4'

SUBNET_MASK_LIST = (
"255.0.0.0",
"255.128.0.0",
"255.192.0.0",
"255.224.0.0",
"255.240.0.0",
"255.248.0.0",
"255.252.0.0",
"255.254.0.0",
"255.255.0.0",
"255.255.128.0",
"255.255.192.0",
"255.255.224.0",
"255.255.240.0",
"255.255.248.0",
"255.255.252.0",
"255.255.254.0",
"255.255.255.0",
"255.255.255.128",
"255.255.255.192",
"255.255.255.224",
"255.255.255.240",
"255.255.255.248",
"255.255.255.252")

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
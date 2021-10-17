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
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with volian.  If not, see <https://www.gnu.org/licenses/>.

import os.path
from subprocess import run, PIPE
from shutil import copy
import sys
import os
import requests
from const import SUBNET_MASK_LIST, SUBNET_MASK_DICT
from func import ask
import re
from time import sleep

# Initially we are only going to support ethernet.
# I want to get this finished but wifi will be a feature we'll add in the future.

interfaces = os.listdir('/sys/class/net/')

def get_eth_list():
	for inter in interfaces:
		if inter.startswith('e'):
			pass
		if inter.startswith('w'):
			pass

def test_network():
	'returns true if we can contact debian'
	try:
		requests.get('http://deb.debian.org', timeout=5)
		return True
	except:
		return False

def get_static_information():
	'asks user and returns tuple with ip, subnet, gateway, domain, search'
	while True:
		try:
			while True:
				ip = input("\nenter your ip address: ")
				if validate_ipv4(ip):
					break
				else:
					print("ip address not valid.. try again..")

			while True:
				subnet = input("\nenter your subnet mask: ")
				if subnet in SUBNET_MASK_LIST:
					break
				else:
					print("subnet mask is not valid.. try again..")
			
			while True:
				gateway = input("\nenter your gateway address: ")
				if validate_ipv4(gateway):
					break
				else:
					print("gateway not valid.. try again..")

			if ask("would you like to enter a domain"):
				try:
					while True:
						domain = input("\nenter your domain name: ")
						try:
							domain = re.fullmatch('[a-zA-Z\d-]{,63}(\.[a-zA-Z\d-]{,63})*', domain).string
							break
						except AttributeError:
							print("domain isn't valid.. try again")
							print("example: debian.org")
				# If we use Ctrl+C we will drop from search configuation and set it to false
				except KeyboardInterrupt:
					domain = False
					print("\nexiting domain setup.")

			else:
				domain = False
			
			if ask("would you like to define a search domain"):
				try:
					while True:
						try:
							search = input("\nenter your search domain: ")
							search = re.fullmatch('[a-zA-Z\d-]{,63}(\.[a-zA-Z\d-]{,63})*', search).string
							break
						except AttributeError:
							print("domain isn't valid.. try again")
							print("example: debian.org")
				# If we use Ctrl+C we will drop from search configuation and set it to false
				except KeyboardInterrupt:
					search = False
					print("exiting search setup.")
			else:
				search = False
		# If we use Ctrl+C it will restart
		except KeyboardInterrupt:
			print("\nrestarting static configuration")
			# We set a sleep so you can Ctrl+C again to exit the function
			sleep(2)
			continue

		print("\nstatic configuration:\n")
		print(f"ip address: {ip}\nsubnet mask: {subnet}\ngateway: {gateway}\ndomain: {domain}\nsearch: {search}")
		if ask("are these settings correct"):
			return ip, subnet, gateway, domain, search
		else:
			print("restarting")
	
def validate_ipv4(ip: str):
	# Check if we have 3 octets and return False if not
	if ip.count(".") == 3:
		ip_adder = ip.split('.')
		for octet in ip_adder:
			# Make sure our octet is actually an integer
			try:
				octet = int(octet)
			except ValueError:
				return False
			# Return false if our octet is outside the range
			if octet < 0 or octet > 255:
				return False
		# If our for loop doesn't fail then we're good
		return True
	else:
		return False

try:
	ip, subnet, gateway, domain, search = get_static_information()
except KeyboardInterrupt:
	print("\nexiting gracefully")
	exit(0)


print(ip)
print(subnet)
print(gateway)
print(domain)
print(search)

# INTERFACE_HEADER = (
# "# This file describes the network interfaces available on your system\n"
# "# and how to activate them. For more information, see interfaces(5).\n"
# "\nsource /etc/network/interfaces.d/*\n")


# f"ip addr add {ip}/{subnet} dev {interface}"
# f"ip link set {interface} up"
# f"ip route add default via {gateway} dev {interface}"



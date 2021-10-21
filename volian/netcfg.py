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

from genericpath import exists
import os.path
from subprocess import run, PIPE
from shutil import copy, rmtree
import sys
import os
import requests

from func import ask
import re
from time import sleep
from subprocess import run
from ipaddress import ip_interface, ip_address, ip_network

from volian.constant import RESOLV_CONF, SUBNET_MASK_DICT
from volian.logger import eprint, wprint

# Initially we are only going to support ethernet.
# I want to get this finished but wifi will be a feature we'll add in the future.

interfaces = os.listdir('/sys/class/net/')

def get_eth_list():
	'returns a list of ethernet interfaces'
	eth_list = []
	for inter in interfaces:
		if inter.startswith('e'):
			eth_list.append(inter)
		# Probably will leave this here until I implement wifi support
		if inter.startswith('w'):
			pass
	return eth_list

def test_network():
	'returns true if we can contact debian'
	try:
		requests.get('http://deb.debian.org', timeout=5)
		return True
	except:
		return False

def get_static_information():
	'asks user and returns tuple with ip, subnet, gateway, domain, search, dns'
	while True:
		# Try statement for handling KeyboardInterrupt. Restarts get_static_information
		# See the except: for more information
		try:
			# Start by getting an IP address and making sure it's valid
			while True:
				try:
					ip = ip_address(input("\nenter your ip address: "))
					break
				except ValueError:
					eprint("ip address not valid.. try again..")

			# Get a subnet for the address. both notations are accepted
			# Examples: 255.255.255.0 or /24
			while True:
				subnet = input("\nregular and slash notation accepted\nenter your subnet mask: ")
				if subnet in SUBNET_MASK_DICT.keys():
					subnet = SUBNET_MASK_DICT.get(subnet)
					break
				elif subnet in SUBNET_MASK_DICT.values():
					break
				else:
					eprint("subnet mask not valid.. try again..")
			
			# Get the Gateway information and check it against the given IP and Subnet Mask
			while True:
				try:
					gateway = ip_address(input("\nenter your gateway address: "))
				except ValueError:
					eprint("gateway not valid.. try again..")
					continue
				if gateway != ip:
					interface = ip_interface(str(ip)+subnet)
					if ip_address(gateway) in ip_network(interface.network):
						break
					else:
						eprint("gateway not in network.. try again..")
				else:
					eprint("gateway can't be the same as the ip address.. try again..")

			# Get domain name and make sure it's valid. 
			if ask("would you like to enter a domain"):
				try:
					while True:
						domain = input("\nenter your domain name: ")
						try:
							domain = re.fullmatch('[a-zA-Z\d-]{,63}(\.[a-zA-Z\d-]{,63})*', domain).string
							break
						except AttributeError:
							eprint("domain isn't valid.. try again")
							eprint("example: debian.org")
				# If we use Ctrl+C we will drop from search configuation and set it to false
				except KeyboardInterrupt:
					domain = None
					wprint("\nexiting domain setup.")
			else:
				domain = None

			# Get search domain and check that it's valid.
			if ask("would you like to define a search domain"):
				try:
					while True:
						try:
							search = input("\nenter your search domain: ")
							search = re.fullmatch('[a-zA-Z\d-]{,63}(\.[a-zA-Z\d-]{,63})*', search).string
							break
						except AttributeError:
							eprint("domain isn't valid.. try again")
							eprint("example: debian.org")
				# If we use Ctrl+C we will drop from search configuation and set it to false
				except KeyboardInterrupt:
					search = None
					wprint("exiting search setup.")
			else:
				search = None
			# Get dns information. Set to default if no
			if ask("default is google dns 8.8.8.8\nwould you like to define a dns server"):
				try:
					while True:
						try:
							nameserver = ip_address(input("\nenter your dns server: "))
						except AttributeError:
							eprint("dns server isn't valid.. try again")
							eprint("example: 8.8.8.8")
				except KeyboardInterrupt:
					nameserver = '8.8.8.8'
					wprint("exiting dns setup.. using default dns")
			else:
				nameserver = '8.8.8.8'
		# If we use Ctrl+C it will restart
		except KeyboardInterrupt:
			print("\nrestarting static configuration")
			# We set a sleep so you can Ctrl+C again to exit the function
			sleep(2)
			continue

		print("\nstatic configuration:\n")
		print(f"ip address: {ip}\nsubnet mask: {subnet}\ngateway: {gateway}\ndomain: {domain}\nsearch: {search}")
		if ask("are these settings correct"):
			return ip, subnet, gateway, domain, search, nameserver
		else:
			wprint("restarting")
	
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

def configure_static_network(interface, ip, subnet_mask, gateway, domain=None, search=None, nameserver='8.8.8.8'):
	"""
	Configures the static network. If subnet is not slash notation it will be converted.

	Returns true if connection works. false if not.

	Default nameserver will be Google 8.8.8.8
	"""

	run(["ip", "addr", "add", f"{ip}{subnet_mask}", "dev", f"{interface}"]).check_returncode
	run(["ip", "link", "set", f"{interface}", "up"]).check_returncode
	run(["ip", "route","add", "default", "via", f"{gateway}", "dev", f"{interface}"]).check_returncode

	with open(RESOLV_CONF, 'w')as file:
		file.write(f"nameserver {nameserver}")
		if search is not False:
			file.write(f"search {search}")

	if test_network():
		return True
	else:
		# Reverse configuration
		run(["ip" "route", "del", f"{gateway}{subnet_mask}", "dev", f"{interface}"]).check_returncode
		run(["ip", "link", "set", f"{interface}", "down"]).check_returncode
		run(["ip", "addr", "del", f"{ip}{subnet_mask}", "dev", f"{interface}"]).check_returncode

		# Check if the file exists and remove it. It should exist but ya know
		if exists(RESOLV_CONF):
			rmtree(RESOLV_CONF)

		return False

def configure_dhcp_network(interface):

	# Attempt to configure network with dhcp
	run([f"dhclient", "-1", f"{interface}"]).check_returncode

	if test_network():
		return True
	else:
		# Time to reverse our configurations if it didn't work.

		# It's possible the lot of these could fail due to not being configured at all.
		# We don't want this to hold us up if it does fail so we're going to wrap each of these in a try, except, pass
		try:
			# Get dhcp interfaces IP address so that we can remove it.
			ip_parse = run(["ip", "addr", "show", "dev", f"{interface}"], stdout=PIPE).stdout.decode().split('\n')
			for entry in ip_parse:
				if 'inet' in entry and 'inet6' not in entry:
					dhcp_ip_list = entry.split()[1].split("/")
					subnet_mask = '/'+dhcp_ip_list[1]
					ip = dhcp_ip_list[0]
		except:
			wprint(f"failed to find ip address for {interface}")
	
		try:
			# Get the default gateway as well
			default_gateway_parse = run(["ip", "route", "show", "dev", f"{interface}"], stdout=PIPE).stdout.decode().split('\n')
			for entry in default_gateway_parse:
				if 'default' in entry:
					gateway = entry.split()[2]
		except:
			wprint(f"failed to find default gateway for {interface}")
		
		# Now we can put our variables to use
		try:
			run(["ip" "route", "del", f"{gateway}{subnet_mask}", "dev", f"{interface}"]).check_returncode
		except:
			wprint("failed to remove default gateway")

		try:
			run(["ip", "link", "set", f"{interface}", "down"]).check_returncode
		except:
			wprint("failed to shutdown interface")

		try:
			run(["ip", "addr", "del", f"{ip}{subnet_mask}", "dev", f"{interface}"]).check_returncode
		except:
			wprint("failed to remove ip address")

		# If resolve.conf exists we should probably remove it.
		if exists(RESOLV_CONF):
			rmtree(RESOLV_CONF)

		return False

def initial_network_configuration():
	print()
	# Print a new line to add some separation and notify the user of some things.
	wprint("only a wired ethernet connection is supported at the moment")
	wprint("network configuration is going to be for the installer environment")
	wprint("as well as your final installed system")

	if not ask("is this okay"):
		print("I get it, we're not good enough for you.. exiting..")
		exit(0)

	# If less than 1 interface we can't really continue
	eth_list = get_eth_list()
	if len(eth_list) < 1:
		eprint("looks like we don't have any ethernet devices..")
		eprint("You need ethernet interface to continue.. exiting")
		exit(1)

	# Can't really test more than one at the moment, But I will soon.
	# if we have more than one interface we need the user to choose the primary interface.
	elif len(eth_list) > 1:
		while True:
			sum = -1
			for eth in eth_list:
				sum = sum +1
				print(f"{sum} {eth}")



	else:
		interface = eth_list[0]
		print("there seems to be only one ethernet interface")
		print(f"using ethernet {interface}")

	# Begin the network process.
	while True:

		# Choose network interface
		interface = None

		# Setup network
		try:
			if ask("y = dhcp\n n = static\nwould you like to setup the network using dhcp"):
				if configure_dhcp_network(interface):
					print("connection secured. continuing")
					break
			else:
				ip, subnet, gateway, domain, search, nameserver = get_static_information()
				configure_static_network(interface, ip, subnet, gateway, domain, search, nameserver)

		except KeyboardInterrupt:
			wprint("you must have a configured network to continue")
			# sleep for 2 seconds on restarting the loop in case they want to drop to a shell or restart the whole process
			sleep(2)
			continue


INTERFACE_HEADER = (
"# This file describes the network interfaces available on your system\n"
"# and how to activate them. For more information, see interfaces(5).\n"
"\nsource /etc/network/interfaces.d/*\n")

def main():
	eprint("netcfg isn't intended to be run directly.. exiting")
	exit(1)
if __name__ == "__main__":
	main()
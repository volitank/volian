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
	print("utils isn't intended to be run directly.. exiting")
	exit(1)

from subprocess import run
from math import trunc
from pathlib import Path
from getpass import getpass
from logger import eprint, wprint
from time import sleep

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

def ask_list(ask_list: list, name: str):
	"""Takes a list, prints it all to the screen and asks the user to choose one.
	
	Arguments:
		ask_list: A list you would like to iterate to a user
		name: name to go in the message sent to the user.

		returns users choice from the list
	Message::

	f"please select the number of the {name} you would like to use: "
	"""
	while True:
		sum = -1
		for item in ask_list:
			sum = sum +1
			print(f"{sum} {item}".rstrip())
		try:
			resp = int(input(f"please select the number of the {name} you would like to use: "))
			if resp in range(0, len(ask_list)):
				return ask_list[resp]
			else:
				eprint("That choice wasn't on the list.. Trying again")
				sleep(2)
		except ValueError as e:
			eprint("\nchoice must be a number.. Trying again")
			sleep(2)
		except IndexError as e:
			eprint("\nthat choice wasn't in the list.. Trying again")
			sleep(2)

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

def get_password():
	"Asks user for password, confirms it and returns it"
	while True:
		password = getpass("password:")
		confirmpass = getpass("confirm password:")
		if password == confirmpass:
			print("passwords match")
			return password
		del password
		eprint("passwords don't match! try again.")

def main():
	eprint("func isn't intended to be run directly.. exiting")
	exit(1)
if __name__ == "__main__":
	main()
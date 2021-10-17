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

def parse_mirror_master():
	with open('Mirrors.masterlist', 'r') as mirror_list:
		data = mirror_list.read()
		# Split data into list by empty line
		split_data = data.split('\n\n')
		# Remove all empty entries from the list
		split_data = list(filter(('').__ne__, split_data))	
		return split_data

def get_country_list(split_data, arch):
	'Takes our initally parsed mirror list and returns a list of countries'
	country_set = set()

	# Split data into their own comfy list
	for n in range(0, len(split_data)):
		mirror_data = split_data[n].splitlines()

		# We get all of the applicable repos and then put their country in a set
		# The set doesn't allow for duplicates so we can get a consise list
		if arch in str(mirror_data) and 'Archive-http:' in str(mirror_data):
			if 'Country' in mirror_data[1]:
				# We take the data, remove Country header, strip white space and the country code
				add_set = mirror_data[1].replace('Country:', '').strip()[3:]
				country_set.add(add_set)
			if 'Country' in mirror_data[2]:
				# Country may be in the third place, so just to be sure we do a chekc here too
				add_set = mirror_data[2].replace('Country:', '').strip()[3:]
				country_set.add(add_set)
		# We need it a list so we convert it back and then sort alphabetically
		country_list = list(country_set)
		country_list.sort()
	return country_list

def ask_list(ask_list, name):
	'Asks the '
	while True:
		sum = -1
		for item in ask_list:
			sum = sum +1
			print(f"{sum} {item}".rstrip())
		try:
			resp = int(input(f"please select the number of the {name} you would like to use: "))
			if resp in range(0, 64):
				return ask_list[resp]
			else:
				print("That choice wasn't on the list.")
		except ValueError as e:
			from time import sleep
			print("\nchoice must be a number.. Trying again")
			sleep(2)
		except IndexError as e:
			from time import sleep
			print("\nthat choice wasn't in the list.. Trying again")
			sleep(2)

def get_url_list(split_data, country, arch):
	'Takes our initally parsed mirror list and returns a list of urls in the country we choose'
	url_list = []
	for n in range(0, len(split_data)):
		mirror_data = split_data[n].splitlines()
		if arch in str(mirror_data) and 'Archive-http:' in str(mirror_data):
			if country in str(mirror_data):
				url_list.append(mirror_data[0].replace('Site:', '').strip())
	return url_list

# split_data = parse_mirror_master()
# country_list = get_country_list(split_data)
# country = ask_list(country_list, 'country')
# url_list = get_url_list(split_data, country)
# url = ask_list(url_list, 'mirror')
# print(url)
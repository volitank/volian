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
from pydoc import pager
from pathlib import Path
from sys import stderr, argv

from constant import RELEASE_OPTIONS, LICENSE

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
			dest=argparse.SUPPRESS,
			default=argparse.SUPPRESS,
			help="show release options and exit"):
		super(releaseOptions, self).__init__(
			option_strings=option_strings,
			dest=dest,
			default=default,
			nargs=0,
			help=help)

	def __call__(self, parser, args, values, option_string=None):
		setattr(args, self.dest, values)
		print(RELEASE_OPTIONS)
		parser.exit()

# Custom Action for --license switch
class GPLv3(argparse.Action):
	def __init__(self,
			option_strings,
			dest=argparse.SUPPRESS,
			default=argparse.SUPPRESS,
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

def arg_parse():

	formatter = lambda prog: argparse.HelpFormatter(prog,
													max_help_position=64)
	bin_name = Path(argv[0]).name
	version = 'v0.01'
	parser = volianParser(	formatter_class=formatter,
							usage=f'{bin_name} <distro> [--options]'
							)

	parser.add_argument('distro', choices=['ubuntu', 'debian'], metavar='<debian|ubuntu>')
	parser.add_argument('--release', nargs='?', metavar='release', help='choose your distro release. stable is default for Debian. latest LTS for Ubuntu')
	# Taking out --no-part for now. We won't be using it at the moment and likely will remove it completely in the future. Not sure
#	parser.add_argument('--no-part', action="store_true", help="using this switch will skip partitioning")
	parser.add_argument('--minimal', action='store_true', help="uses the variant=minbase on the backend of debootstrap. Only use this if you're sure you want it")
	parser.add_argument('--version', action='version', version=f'{bin_name} {version}')
	parser.add_argument('--release-options', action=releaseOptions)
	parser.add_argument('--license', action=GPLv3)

	return parser

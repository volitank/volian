import logging

volian_log = logging
volian_log.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO, datefmt='[%Y-%m-%d %H:%M:%S]')

eprint = volian_log.error
vprint = volian_log.info
wprint = volian_log.warning

def main():
	eprint("logger isn't intended to be run directly.. exiting")
	exit(1)
if __name__ == "__main__":
	main()
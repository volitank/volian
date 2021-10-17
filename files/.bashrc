# shellcheck shell=bash
# Volian bashrc
# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
# There are some fringe cases where not having this can cause issues
# scp is potential case.
case $- in
    *i*) ;;
      *) return;;
esac

export PATH=$PATH:\
/usr/local/sbin:\
/usr/local/bin:\
/snap/bin:\
/usr/sbin:\
/usr/bin:\
/sbin:\
/bin:\
~/.bin:\
~/.local/bin

## History Channel
# Eternal bash history.
# ---------------------
# You can comment out this section to use bash defaults.
# Undocumented feature which sets the size to "unlimited".
# http://stackoverflow.com/questions/9457233/unlimited-bash-history
export HISTFILESIZE=
export HISTSIZE=
export HISTTIMEFORMAT="[%F %T] "
# Change the file location because certain bash sessions truncate .bash_history file upon close.
# http://superuser.com/questions/575479/bash-history-truncated-to-500-lines-on-each-login
export HISTFILE=~/.bash_eternal_history
# Erasedups is cool because we won't keep duplicate commands
# The 4 thousand times you typed ls -lah will only be in there once.
export HISTCONTROL=erasedups
# Force prompt to write history after every command.
# http://superuser.com/questions/20900/bash-history-loss
PROMPT_COMMAND="history -a; $PROMPT_COMMAND"

# Make less more friendly for non-text input files, see lesspipe(1)
# An example is opening .deb files with less. Without this it's just binary garbage
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# Enable bash completion just in case it's not by default.
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
	. /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
	. /etc/bash_completion
  fi
fi

# Enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
	test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
	alias ls='ls --color=auto'
	alias dir='dir --color=auto'
	alias vdir='vdir --color=auto'

	alias grep='grep --color=auto'
	alias fgrep='fgrep --color=auto'
	alias egrep='egrep --color=auto'
fi

# Some special secret aliases
# some more ls aliases
alias dd='dd status=progress'
alias diskspace='du -hd 1 | sort -n -r'
# If we don't have vim.basic but we do have vim.tiny then alias vim to vim.tiny
[ -x /usr/bin/vim.basic ] || [ -x /usr/bin/vim.tiny ] && alias vim='vim.tiny'
# This sudo space is to allow you to use sudo with aliases
# Example: sudo diskspace
alias sudo='sudo '

# Alias definitions.
# You may want to put all your additions into a separate file like
# ~/.bash_aliases, instead of adding them here directly.
# See /usr/share/doc/bash-doc/examples in the bash-doc package.
if [ -f ~/.bash_aliases ]; then
	. ~/.bash_aliases
fi

# Simple portable check to see if we have color support
if [ -x /usr/bin/tput ] && tput setaf 1 >&/dev/null; then
# We have color support; assume it's compliant with Ecma-48
# (ISO/IEC-6429). (Lack of such support is extremely rare, and such
# a case would tend to support setf rather than setaf.)
	color_prompt=yes
else
	color_prompt=
fi

# This adds a percentage bar so you know how far in the page you are.
export MANPAGER='less -s -M +Gg'
# Set 'man' colors
if [ "$color_prompt" = yes ]; then
	man() {
	env \
	LESS_TERMCAP_mb="$(tput bold; tput setaf 1)" \
	LESS_TERMCAP_md="$(tput bold; tput setaf 4)" \
	LESS_TERMCAP_me="$(tput sgr0)" \
	LESS_TERMCAP_se="$(tput sgr0)" \
	LESS_TERMCAP_so="$(tput bold; tput setaf 3; tput setab 4)" \
	LESS_TERMCAP_ue="$(tput sgr0)" \
	LESS_TERMCAP_us="$(tput bold; tput setaf 2)" \
	man "$@"
	}
fi

PROMPT_COMMAND=__prompt_command    # Function to generate PS1 after CMDs

# This function controls drawing our prompt
__prompt_command() {
    local EXIT="$?"                # This needs to be first

	# Prints a new line (\n) if one didn't exist
	# Not harmful either way, but can be annoying
    PS1='$(printf "%$((COLUMNS-1))s\r")'
	# Uncomment this to disable printing new line
	#PS1=''

	# Basic shell colors you can choose from. In our vars below
	# We are using the setaf codes
	#
	# # Regular Colors						# tput setaf code
	# "BLACK": "30",			# BLACK			0
	# "RED": "31",				# RED			1
	# "GREEN": "32",			# GREEN			2
	# "YELLOW": "33",			# YELLOW		3	
	# "BLUE": "34",				# BLUE			4
	# "PURPLE": "35",			# PURPLE		5	
	# "CYAN": "36",				# CYAN			6
	# "WHITE": "37",			# WHITE			7
	# "INTENSE_BLACK": "90",	# BLACK			8
	# "INTENSE_RED": "91",		# RED			9
	# "INTENSE_GREEN": "92",	# GREEN			10
	# "INTENSE_YELLOW": "93",	# YELLOW		11	
	# "INTENSE_BLUE": "94",		# BLUE			12
	# "INTENSE_PURPLE": "95",	# PURPLE		13	
	# "INTENSE_CYAN": "96",		# CYAN			14
	# "INTENSE_WHITE": "97",	# WHITE			15

	local bold="\[$(tput bold)\]"
	local reset="\[$(tput sgr0)\]"
	local green="\[$(tput setaf 10)\]"
	local blue="\[$(tput setaf 12)\]"
	local yellow="\[$(tput setaf 11)\]"
	local white="\[$(tput setaf 15)\]"
	local red="\[$(tput setaf 1)\]"

	# Define basic colors to be used in prompt
	## The color for username (light_blue, for root user: bright_red)
	local username_color="${reset}${white}\$([[ \${EUID} == 0 ]] && echo \"${reset}${bold}${red}\")";
	## Color of @ and ✗ symbols (special_yellow)
	local at_color=$reset$bold$yellow
	## Color of host/pc-name (green)
	local host_color=$reset$bold$green
	## Color of current working directory (light_purple)
	local directory_color=$reset$bold$green
	## Color for other characters (like the arrow)
	local line_color=$reset$bold$blue
	# The last symbol in prompt ($, for root user: #)
	local symbol="${at_color}$(if [[ ${EUID} == 0 ]]; then echo '#'; else echo '$'; fi)"

	# Exit symbol
	exit_symbol=$EXIT

	# Uncomment to easily change the exit status to an x, or whatever you like
	#exit_symbol='x'

	# Uncomment this to disable the failed exit prompt all together
	#local EXIT=0

	# If we have support for color then we will do color prompt things 
	if [ "$color_prompt" = yes ]; then
		# Check if our exit code is 0 (Success)
		if [ $EXIT != 0 ]; then
			# If exit code is not 0 (Failure) Then we will draw our exit symbol
			PS1+="${line_color}┌─[${reset}${bold}${red}${exit_symbol}${line_color}]─[";
		else
			# If exit code is 0 (Success) we draw our normal prompt
			PS1+="${line_color}┌─[";
		fi
		# This is the rest of our prompt that stays the same no matter exit status
		PS1+="${username_color}\u"; # \u=Username
		PS1+="${at_color}@";
		PS1+="${host_color}\h" #\h=Host
		PS1+="${line_color}]-[";
		PS1+="${directory_color}\w"; # \w=Working directory
		PS1+="${line_color}]\n└──╼ "; # \n=New Line
		PS1+="${symbol}${reset}"
	else
		# If we don't have color support (Probably unlikely) we will draw a basic prompt
		# We can still do exit codes! Just not as pretty
		if [ $EXIT != 0 ]; then
			# If exit code is not 0 (Failure) Then we will draw our exit symbol
			PS1+="┌─[${exit_symbol}]─[";
		else
			# If exit code is 0 (Success) we draw our normal prompt
			PS1+="┌─[";
		fi
		# This is the exact same as the color prompt minus the colors.
		PS1+="\u@\h]-[\w]\n└──╼ "
	fi
}
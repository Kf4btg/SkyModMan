#!/bin/bash

## Custom-made Mod Manager for Skyrim. 
## BEFORE USING:
## Use this command and the "lowercasify" script to rename all files in the Data dirs:
## cd $MODPATH; for ddir in ./*/Data/; do cd "$ddir"; lowercasify; cd ../../ ; done
## FIXME: automate this!


## TODO: create a config file to hold defaults for these vars
CONFIG_DIR="${XDG_CONFIG_HOME}/skymodman"
CONFIG_FILE="${CONFIG_DIR}/skymodman.conf"

## (WPP = Directory containing wineprefixes, hopefully defined in .bashrc)
## FIXME: allow WPP to be set/overridden from command line
SKYPATH="$WPP/skyrim/drive_c/Program Files/Steam/SteamApps/common"			## Location of Main Skyrim Folder (i.e. dir which contains the "Skyrim" folder)
MODPATH="/media/jindows/ManjaroSteamStuff/Skyrim_OtherStuff/unpackedMods"	## Location of Unpacked Mods
VIRTPATH="${SKYPATH}/SkyModMan_rundir"			## Location of "Virtual" Skyrim Folder

MODSLIST="$MODPATH"/_mods.list					## Mods List File
INSTALL_ORDER="$MODPATH"/_install_order.ini		## Install Order
LOAD_ORDER="$MODPATH"/_load_order.ini			## Load Order
OW_FILE="$MODPATH"/_overwrites.txt				## File listing overwritten mod parts

main() {
	# create_vdir
# 	echo -n ""

	check_config	## check for config folder and file, create them if not present.
	#ow_log "wrote config file"
	read_config		## 
}

usage() {
	cat << _USAGE
    SkyModMan - create a virtual directory-structure for Skyrim containing desired mods, 
        leaving the original install directory untouched.

Synopsis

	SkyModMan [-h|--help]
	SkyModMan [-s DIR] [-m DIR] [-l FILE] [-i FILE] [-o FILE] [-w FILE] -v DIR

Options

	-h, --help
		Show this help information.

	-s, --skypath=DIRECTORY
		Specifies DIRECTORY as the folder containing the Skyrim install.

	-m, --modpath=DIRECTORY
		Specifies DIRECTORY as the folder containing unpacked Mod folders.

	-l, --modlist=FILE
		Use FILE to store the list of mods found in the modpath.

	-i, --install=FILE
		Read the mod install-order from FILE.

	-o, --load=FILE
		Read the mod load-order from FILE.

	-w, --owlog=FILE
		Use FILE to log any overwrites that occur during mod installation.
		Which mods overwrite others is determined from the install order.

	-v, --virtpath=DIRECTORY
		Specify DIRECTORY as the location of the "virtual" Skyrim install.

Known Bugs

	The long options don't actually work...
_USAGE
}

check_config() {
	
# 	if [ ! -d "$CONFIG_DIR" ]; then
# 		mkdir -p "$CONFIG_DIR"
# 	fi
	
	[ -d "$CONFIG_DIR" ] || mkdir -p "$CONFIG_DIR"
	
	[ -f "$CONFIG_FILE" ] || create_default_config
}

create_default_config() {
	## initially, set all folders and files to be inside the config folder.
	## Obviously, some of these must be changed by user.

echo "SkyModMan configuration file not found. Creating default config at $CONFIG_FILE. Please edit this file to set your preferred paths, then run SkyModMan again."

cat << _CONFIG > "$CONFIG_FILE"
SKYPATH=$CONFIG_DIR/Skyrim
MODPATH=$CONFIG_DIR/mods
VIRTPATH=$CONFIG_DIR/VSkyrim
MODSLIST=$CONFIG_DIR/mods.list
INSTALL=$CONFIG_DIR/install_order.ini
LOAD=$CONFIG_DIR/load_order.ini
OW_FILE=$CONFIG_DIR/overwrites.txt
_CONFIG
}

read_config() {
	while IFS='=' read VNAME VVAL ; do declare $VNAME=$VVAL; done < "$CONFIG_FILE"

# 	echo $SKYPATH
# 	echo $MODPATH
# 	echo $VIRTPATH
# 	echo $MODSLIST
# 	echo $INSTALL
# 	echo $LOAD
# 	echo $OW_FILE

#	cat $CONFIG_FILE | cut -d "=" -f 1,2 | while read VNAME VVAL; do echo $VNAME $VVAL; done
}


# TODO: allow specification of variables on command line
create_vdir() {
cd "$MODPATH"

## Populate MODSLIST with folders found in MODPATH
[ -f "$MODSLIST" ] && rm "$MODSLIST"
find . -mindepth 1 -maxdepth 1 -type d | while IFS= read -r NAME ; do
    echo $(basename "$NAME") >> "$MODSLIST"
done

## Create INSTALL_ORDER file if it doesn't exist
## TODO: check for new mods and add them to the list, re-prompt for edit
if [[ ! -f "$INSTALL_ORDER" ]] ; then
    cp "$MODSLIST" "$INSTALL_ORDER"
    echo "No Install Order file found. Please edit $INSTALL_ORDER with your desired mod install order."
else
	## Create the virtual directory structure
    echo "Creating virtual mod file structure..."
    echo "Using install order from: $INSTALL_ORDER"
    echo "Virtual Skyrim Install: $VIRTPATH"

    ## Remove old structure
    rm -rf "$VIRTPATH"/*
    [ -f "$OW_FILE" ] && rm "$OW_FILE"

    cd "$SKYPATH/Skyrim"
#    cd "Skyrim/"
    ## First, simply link all files & dirs directly under "Skyrim/"
    for f in ./* ; do
	ln -s "$SKYPATH/Skyrim/$f" "$VIRTPATH"/"$f"
    done
    ## ...except for the Data folder
    rm "$VIRTPATH/Data"

    ## Create Skyrim/Data directory structure
    rsync -r -f"+ */" -f"- *" "Data" "$VIRTPATH"

    ## Link files from Skyrim Data folder
    find Data/ \( -type f -o -type l \) | while IFS= read -r FILE; do
	ln -s "$SKYPATH/Skyrim/$FILE" "$VIRTPATH"/"$FILE"
    done

   # read -p "waiting..."

    ## Change all files to lowercase
    cd "$VIRTPATH/Data"
    lowercasify

   # read -p "waiting..."

    ## Create mod dir structure
    ## TODO: allow exclusion of mods in INSTALL_ORDER file
    cd "$MODPATH"
    while read MOD ; do
		rsync -r -f"+ */" -f"- *" "$MOD/Data" "$VIRTPATH"
    done < "$INSTALL_ORDER"

    ## Link files, record overwrites
    while read MOD ; do
	cd "$MODPATH"/"$MOD"
	find Data/ -type f | while IFS= read -r MODFILE; do
	    if [[ -e "$VIRTPATH/$MODFILE" ]] ; then ##collision (overwrite) occurred
			O_FILE=$(readlink -e "$VIRTPATH/$MODFILE") #Original file
			O_MOD=$(echo "$O_FILE" | sed 's@'"$MODPATH/"'\|'"$SKYPATH/"'@@g' | awk -F '/' '{ print $1 }') #Original mod

			## Record overwrite (original + replacement)
			echo "\"$MOD\" has overwritten this file from \"$O_MOD\":" >> "$OW_FILE"
			echo ">>> $MODFILE" >> "$OW_FILE"
			echo >> "$OW_FILE"
			ln -sf "$MODPATH"/"$MOD"/"$MODFILE" "$VIRTPATH"/"$MODFILE"
	    else
			ln -s "$MODPATH"/"$MOD"/"$MODFILE" "$VIRTPATH"/"$MODFILE"
	    fi
	done
	    #-exec ln -s "$MODPATH"/"$MOD"/{} "$VIRTPATH"/{} \;
    done < "$INSTALL_ORDER"

    [ -f "$OW_FILE" ] && echo "Overwrites occurred. Please check $OW_FILE to make sure that the proper replacements were made."

fi
}

ow_log() { #PARAMS: message

	local log_msg="${1:-''}"
	echo "$log_msg" >> "$OW_FILE"
}

#[ $# -eq 0 ] && usage

while getopts :hs:m:v:l:i:o:w: OPT; do
	case $OPT in
		h|+h)
			usage
		;;
		s|+s)
		"$OPTARG"
		;;
		m|+m)
		"$OPTARG"
		;;
		v|+v)
		"$OPTARG"
		;;
		l|+l)
		"$OPTARG"
		;;
		i|+i)
		"$OPTARG"
		;;
		o|+o)
		"$OPTARG"
		;;
		w|+w)
		"$OPTARG"
		;;
		*)
			echo "Unknown command '$OPTARG'"
			usage
			exit 2
	esac
done
shift $(( OPTIND - 1 ))
OPTIND=1

main

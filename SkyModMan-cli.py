#!/usr/bin/env python3

from argparse import ArgumentParser


parser = ArgumentParser(description="create a virtual directory-structure for Skyrim containing desired mods, leaving the original install directory untouched")

parser.add_argument(
    "directory", nargs="?",
    help="Path to the folder where you'd like to create the \"virtual\" Skyrim install (will be created if it doesn't exist).")

parser.add_argument(
    "-s", "--skypath", metavar="DIR",
    help="path to actual Skyrim install")
parser.add_argument(
    "-m", "--modpath", metavar="DIR",
    help="path to folder containing unpacked Mod folders")
parser.add_argument(
    "-l", "--modlist", metavar="FILE",
    help="file in which to store the list of mods found in the modpath")

parser.add_argument(
    "-i", "--install", metavar="FILE",
    help="file from which to read the mod install order")

parser.add_argument(
    "-o", "--load", metavar="FILE",
    help="file from which to read the mod load-order")

parser.add_argument(
    "-w", "--owlog", metavar="FILE",
    help="Use this file to log any overwrites that occur during mod installation. Which mods overwrite others is determined from the install order.")

args = parser.parse_args()

if not args.directory:
    parser.print_help()

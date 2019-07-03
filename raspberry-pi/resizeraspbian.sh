#!/usr/bin/env bash

# This script shrinks a Raspberry Pi Raspbian SD card image (produced by 
# Win32diskimager) down to the minimum size + a buffer so that the image can 
# boot when flashed to a new card. Heavily based on the perl script by DeanC 
# available from https://www.raspberrypi.org/forums/viewtopic.php?p=465398

# Check if we're running as root
if (( $EUID != 0 )); then
	echo "Please run this script as root or with the sudo command."
	exit 1
fi

# Check if a file has been provided
if [ -z "$1" ]; then
	echo "No image file specified."
	exit 1
fi

# Check if the file exists
if [ ! -f "$1" ]; then
	echo "File specified does not exist."
	exit 1
fi

# Get the full path to the file
fpath=`readlink -f "$1"`

# Get just the filename itself
fname=`basename "$1"`

# Length of the filename
fname_length=${#fname}

# Print out a fancy header
echo $fname
printf '=%.0s' $(seq 1 $fname_length); printf '\n'

# Get the size of the existing filesystem
fsys=`parted -m "$fpath" unit B print | grep -E 'ext4'`

# Output: partnum:start:fs_size:?:fs_format::;
# Need to split the output and extract the appropriate field
# Would use readarray, but my system lacks the version required
#readarray -td: fsinfo <<<"$fsys"; declare -p fsinfo;

partnum=`cut -d ":" -f 1 <<<"$fsys"`
start=`cut -d ":" -f 2 <<<"$fsys" | sed 's/[^0-9]*//g'`
fs_size=`cut -d ":" -f 3 <<<"$fsys" | sed 's/[^0-9]*//g'`

printf "Existing file system size: %1.1f MB " $(echo "scale=1; $fs_size/1048576" | bc -l); printf "(%1.2f GB)\n" $(echo "scale=2; $fs_size/1073741824" | bc -l)

# Load the image file to a loopback device
loopback=`losetup -f --show -o $start "$fpath"`;

echo "Mounted image to $loopback";
echo "Checking file system...";

# Check the file system
e2fsck -p -f $loopback > /dev/null 2>&1
fs_check=$?

# If there was a problem, abort the process and unmount the image
if [ $fs_check -ne 0 ]; then
	echo "There was an error in file system that could not be automatically repaired."
	losetup -d $loopback > /dev/null 2>&1
	exit 1
fi

# Get the minimum possible size of the file system
min_size=`resize2fs -P $loopback 2>&1`
min_size=`cut -d ":" -f 2 <<<"${min_size##*$'\n'}" | tr -d '[:space:]'`

# Add safety buffer
min_size=$((min_size+1024))

echo "Resizing (this may take a while)..."
resize2fs -p $loopback $min_size

# Unmount the device
sleep 1
losetup -d $loopback > /dev/null 2>&1

# Calculate the new size of the device
new_size=$(((min_size*4096)+$start))

# Update the partition
parted "$fpath" rm $partnum > /dev/null 2>&1
parted -s "$fpath" unit B mkpart primary $start $new_size > /dev/null 2>&1

# New file system size
new_size=$((new_size+58720257))
printf "New file system size: %1.1f MB " $(echo "scale=1; $new_size/1048576" | bc -l); printf "(%1.2f GB)\n" $(echo "scale=2; $new_size/1073741824" | bc -l)

# Truncate the image file
truncate -s $new_size "$fpath" > /dev/null 2>&1

# Calculate the reduction
diff=$((fs_size-$new_size))
printf "Image file was reduced by %1.1f MB"  $(echo "scale=1; $diff/1048576" | bc -l); printf "(%1.2f GB)\n" $(echo "scale=2; $diff/1073741824" | bc -l)

exit 0;

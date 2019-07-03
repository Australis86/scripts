# Raspberry Pi Scripts
A collection of scripts related to the Raspberry Pi.

### resizeraspbian.sh

This is a bash script heavily based upon DeanC's perl script (available from <https://www.raspberrypi.org/forums/viewtopic.php?p=465398>). It takes an image file produced by Win32DiskImager and shrinks it to its minimum possible size (plus a small buffer so that it can still boot). This can be very useful when swapping SD cards, as they can vary slightly in capacity.

The script still needs thorough testing.

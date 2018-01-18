# Overview
This project is a tool to convert spectool_raw files into Chanalyzer WSX files.

[Spectrum Tools](https://www.kismetwireless.net/spectools/) is a set of utilities for capturing RF spectrum data on Linux. It supports various spectrum analyzer hardware including several Wi-Spy devices (original, 24x, 24x2, DBX, DBX2, 900, 24i) by Metageek LLC and the Ubertooth. Spectrum Tools only supports live capture, but spectral data can be logged using spectool_raw, a command line program within Spectum Tools. spectool_raw is a basic dumper interface that dumps the raw data from the spectrum analyzer hardware into a CSV-like file.

[Chanalyzer](https://www.metageek.com/products/wi-spy/) is Metageek's Windows software for their spectrum analyzers. It is a great interface for viewing spectral data, but files must be in the WSX format to be opened in Chanalyzer. The spec2wsx converter translates the output of spectool_raw into WSX files.

The script is written in Python, and it is heavily customized for a particular project. However, it could easily be modified into a more generic form.


# Basic Usage
1. Give the spectool_raw output file a ".spec" extension and place it in the same directory as the spec2wsxConv.py script. 
2. Run the script using the Python 3 interpreter, and the resulting WSX file will be created.


# Advanced Notes
The spec2wsx converter script currently only supports WiSpy DBx and WiSpy 2.4x hardware. The script needs to be modified to support other devices.

spectool_raw doesn't include a timestamp by default. To assign timestamps to each sweep of data, Spectools needs to be compiled with the edited spectool_raw.c source file in this repository.
Instructions for capturing a spectool_raw file with timestamps:
1. Download the Spectools-2016-01-R1 source code from this page: https://www.kismetwireless.net/download.shtml
2. Replace the spectool_raw.c file with the spectool_raw.c file from this repository. The spectool_raw.c file in this repository contains some modifications to include a timestamp.
3. Compile the Spectrum Tools. Note, it is possible to compile only spectool_raw and not the other tools: 

    1. Install the usb drivers: apt-get install libusb-dev
    2. Run the configure file: ./configure (The output should say: “The following targets are configured: spectool_raw”)
    3. Compile the source: make spectool_raw (only compiles a section of the whole spectools code)
    4. Install the binary: make install (this will allow it to be ran without specifying the path of the executable)

4. Run the spectool_raw program. It is possible to capture in several different modes, but the spec2wsxConv.py script will only handle files capture in the following modes:
	* "Full 2.4GHz Band" (2400MHz-2495MHz @ 333.00KHz, 285 samples)
	* "Full 2.4GHz Band (Turbo)" (2400MHz-2495MHz @ 1000.00KHz, 95 samples)
5. The timestamps created by the modified spectool_raw tool are in UTC. The script makes an attempt to convert the timestamps from UTC to EST/EDT based on the file name. This customization was specific to a particular project and should probably be generalized.

Note that if no timestamps are present, arbitrary timestamp data will be created. 

See the header documentation of the spec2wsxConv.py script for more documentation.

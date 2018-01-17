############################################################################### 
# By: Jamin Turner
# Date: 10-Jan-2018
#
# Description: Python script to convert spectool_raw captures into 
#			Chanalyzer .WSX files
#		The script will look for the first .spec file that is in the same
#			directory and convert it to a .wsx file
#		If the file was captured in Turbo mode (1000KHz, 95 samples per	sweep),
#			it will automatically be subsampled so it can be viewed in 
#			Chanalyzer, which only accepts 286 samples per sweep.
#		If the file doesn't have timestamps, they will be automatically
#			generated based on 2.4x Turbo timing (178 ms per sweep).
#		spectool_raw records timestamps in UTC. The timestamps will be translated
#			to EDT/EST based on the filename. (Only works if filename is in the 
#			format: SpecCap-04Jan2018-16.22.29.spec)
#
###############################################################################

import csv
import sqlite3
import os
import glob
import time

#Search for a .spec file in this directory
try:
	infile = glob.glob("*.spec")[0] #only gets the 1st spec file
except: #executed if try stmt gets error (when no .spec files present)
	print("No input file")
	input() #waits for keypress. keeps cmd window from closing before text is read
	quit()
fname = str(infile)
print("file:", fname)

#Get local time from file name and determine if DST is in effect or not
try:
	tmstruct = time.strptime(fname[8:10]+fname[10:13]+fname[13:17]+fname[18:20]
									+fname[21:23]+fname[24:26], "%d%b%Y%H%M%S")
	etime = time.mktime(tmstruct) #convert struct to seconds since epoch
	tmstruct = time.localtime(etime) #cnvrt back to struct, which populates DST correctly
	if(tmstruct.tm_isdst == 0):
		#DST not in effect on this date
		ltimeOffset = -18000000 #5 hour offset for EST
		print("Converting timestamps from UTC to EST")
	else:
		#DST in effect on this date
		ltimeOffset = -14400000 #4 hour offset for EDT
		print("Converting timestamps from UTC to EDT")
except: #executed if date cant be extracted from file name
	ltimeOffset = 0 #leave time in UTC
	print("Not converting timestamps")

#Using the with statement ensures the file gets closed even if an error occurs
with open(infile, 'r') as specCSV:
	read_data = csv.reader(specCSV, delimiter=' ')
	rownum = 0
	csvData = list(read_data)
	
#determine number of sweeps
num_sweeps = len(csvData) - 4 #first 4 rows are info
print("number of sweeps:", num_sweeps)

#extract device and convert to Chanalyzer format (very finicky!)
device = csvData[1][3].replace("-","") + csvData[1][4]
if(device == "WiSpy24x2"):
	device = device.replace("x", "X")
print("device:", device)

#extract the serial number of the device
serialnum = csvData[2][2]
print("serialnum:", serialnum)

#set device_type_id
if(device == "WiSpy24X2"):
	devicetypeid = 4
elif(device == "WiSpyDBx3"):
	devicetypeid = 10
else:
	devicetypeid = 0
print("devicetypeid:", devicetypeid)

#extract frequency resolution and samples per sweep
freq_resolution = float(csvData[3][6].replace("KHz,",""))
print("freq_resolution:", freq_resolution)
samplesPerSweep = int(csvData[3][7])
print("samplesPerSweep:", samplesPerSweep)

#generate timestamps if file has none
if(csvData[4][0] == "Wi-Spy"):
	print("No timestamps present, generating generic timestamps")
	i = 0
	for row in csvData[4:][:]:
		del row[0:4]
		#generate a timestamp based on Turbo timing with a 2.4x
		row.insert(0, str(1483228800000 + 178 * i) + ":")
		i += 1

#convert sweep data to database format 
#	decimal data -> apply +134 offset -> multiply by 2 -> yields DB format
sweepDataDBformat = []
templist = []
#cut the top 4 info lines out of the sweep data
for row in csvData[4:][:]:
	#extract timestamp, convert to integer, remove ":", offset for local timezone
	timestamp = row[0]
	timestamp = int(timestamp[:-1]) + ltimeOffset
	templist.append(timestamp)
	#extract sweep values and convert to DB format
	for value in row[1:]: #skip iterating over 1st value in list, which is timestamp
		if(value != ""): #this is to mitigate the last char of every sweep being ''
			templist.append((int(float(value))+134)*2)
	templist.append(30) #tack on filler data to get it to 286 samples
	#add this row of converted timestamp and sweep values to master list
	sweepDataDBformat.append(templist)
	templist = []

#subsample Turbo data to get it up to 286 samples
if(samplesPerSweep == 95):
	templist = []
	for row in sweepDataDBformat:
		i = 1
		while(i < samplesPerSweep * 3): #note skip last element, which is filler
			#insert 2 additional copies of each element
			row[i:i] = [row[i], row[i]] 
			#must increment ctr by 3 to get to next elem due to newly inserted values
			i += 3
		templist.append(row)
	sweepDataDBformat = templist
	freq_resolution = 333.252014160156
	samplesPerSweep = 285
	print("Subsampled Turbo Data")


###############################################################################
#Create DB

outfile = infile.replace(".spec", ".wsx")
print("output file:", outfile)

if os.path.exists(outfile):
	os.remove(outfile)

#Connect to the DB, which
sqConn = sqlite3.connect(outfile)
curs = sqConn.cursor()

# Create table
curs.execute('''CREATE TABLE 'db_version' ( 'version' VARCHAR NOT NULL, 
											'feature' VARCHAR NOT NULL )''')
curs.execute('''CREATE TABLE 'device' ( 'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
										'device_type_id' INTEGER NOT NULL REFERENCES device_type (id), 
										'serial_number' VARCHAR, 
										'name' VARCHAR, 
										'address' VARCHAR )''')
curs.execute('''CREATE TABLE 'device_setting' ( 'id' INTEGER PRIMARY KEY NOT NULL, 
								'name' TEXT, 
								'device_id' INTEGER NOT NULL REFERENCES device (id), 
								'setting_id' INTEGER NOT NULL REFERENCES setting (id), 
								'purpose_id' INTEGER NOT NULL REFERENCES device_setting_purpose (id) )''')
curs.execute('''CREATE TABLE 'l_device_setting_purpose' ( 'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
														'name' VARCHAR NOT NULL )''')
curs.execute('''CREATE TABLE 'l_device_type' ( 'id' INTEGER PRIMARY KEY NOT NULL, 
											'name' VARCHAR NOT NULL, 
											'amplitude_offset' FLOAT NOT NULL, 
											'amplitude_resolution' FLOAT NOT NULL, 
											'max_rssi' INTEGER NOT NULL )''')
curs.execute('''CREATE TABLE 'l_sweep_type' ( 'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
											'name' VARCHAR NOT NULL )''')
curs.execute('''CREATE TABLE 'network' ( 'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
										'mac' VARCHAR NOT NULL, 
										'mode' VARCHAR, 
										'alias' VARCHAR )''')
curs.execute('''CREATE TABLE 'network_config' ( 'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
												'network_id' INTEGER NOT NULL REFERENCES network (id), 
												'ssid' VARCHAR NOT NULL, 
												'primary_channel' INTEGER NOT NULL, 
												'secondary_channel' INTEGER NOT NULL, 
												'secondary_channel_valid' INTEGER NOT NULL, 
												'channel_width' INTEGER NOT NULL, 
												'phy_type' INTEGER NOT NULL, 
												'supported_phy_types' VARCHAR NOT NULL, 
												'supported_rates' VARCHAR NOT NULL, 
												'encryption' INTEGER NOT NULL, 
												'authentication' INTEGER NOT NULL, 
												'information_elements' BLOB )''')
curs.execute('''CREATE TABLE 'network_scan' ( 'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
											'network_config_id' INTEGER NOT NULL REFERENCES network_config (id), 
											'rssi' INTEGER NOT NULL, 
											'milliseconds_since_epoch' INTEGER NOT NULL )''')
curs.execute('''CREATE TABLE 'notes' ( 'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
									'device_setting_id' INTEGER NOT NULL REFERENCES device_setting(id), 
									'name' VARCHAR NOT NULL, 
									'details' VARCHAR NOT NULL, 
									'milliseconds_since_epoch' INTEGER NOT NULL, 
									'color' INTEGER NOT NULL, 
									'image' BLOB )''')
curs.execute('''CREATE TABLE 'setting' ( 'id' INTEGER PRIMARY KEY NOT NULL, 
										'name' TEXT, 'starting_frequency_khz' INTEGER NOT NULL, 
										'frequency_resolution_khz' INTEGER NOT NULL, 
										'readings_per_sweep' INTEGER NOT NULL )''')
#Note the sqlite_sequence table is auto created and initialized when a normal table
#	contains the AUTOINCREMENT column. The sqlite_sequence table keeps track of the
#	largest ROWID, and it generally shouldn't be changed using INSERT/UPDATE/DELETE
curs.execute('''CREATE TABLE 'sweep' ( 'id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 
									'device_setting_id' INTEGER NOT NULL REFERENCES device_setting (id), 
									'sweep_type_id' INTEGER NOT NULL REFERENCES l_sweep_type (id), 
									'milliseconds_since_epoch' INTEGER NOT NULL, 
									'sweep_data' BLOB NOT NULL )''')


###############################################################################
#Populate DB
curs.execute('''INSERT INTO db_version VALUES ("1.4","WiSpy"),
											  ("1.0", "Notes"),
											  ("1.5", "Wifi")''')

#Add serial number (value is not consistent across platforms...)
curs.execute('''INSERT INTO device (device_type_id, serial_number) 
					VALUES (?, ?)''', [devicetypeid, serialnum])

curs.execute('''INSERT INTO device_setting (id, device_id, setting_id, purpose_id)
					VALUES (0, 1, 1, 1)''')

curs.execute('INSERT INTO l_device_setting_purpose VALUES (1, "Display")')

#Add device id and device name
curs.execute('INSERT INTO l_device_type VALUES (?, ?, -134.0, 0.5, 255)',
					[devicetypeid, device])

#Add frequency resolution and readings per sweep
curs.execute('INSERT INTO setting VALUES (1, "Full 2.4 GHz Band", 2400000, ?, ?)',
					[freq_resolution, samplesPerSweep + 1])

#Add sweep data
for row in sweepDataDBformat:
	sweepDataBlob = bytes(row[1:]) #create a binary blob of everything but timestamp
	curs.execute('''INSERT INTO sweep (device_setting_id, sweep_type_id, 
				milliseconds_since_epoch, sweep_data) VALUES (0, 1, ?, ?)''', [row[0], sweepDataBlob])

# Save (commit) the changes and close the connection
sqConn.commit()
sqConn.close()

print("Done!")
input() #waits for keypress. keeps cmd window from closing before text is read
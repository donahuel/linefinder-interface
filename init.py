#This file populates a SQLite database with information about various lines
#Authors: Larry Donahue, Malachy Bloom, Michael Yang, Vincent He

from app import db, Line
import numpy as np
import os
import math as m
import time as t

def skim(verbose):
    #Skims files in data folder and stores read line objects in a list, which is returned.
    db.drop_all()
    db.create_all()       

    file_list = []
    for subdir, dirs, files in os.walk(rootdir + "/data"):
        for file in files:
            if file.endswith('.txt'):
                filepath = os.path.join(subdir, file)
                file_list.append(filepath)
    
    os.mkdir("temp") #Creates directory. This directory should not exist at this point.
    tempnum = 1 #A counting variable for the temporary chunk files that will be created.
                
    sig_lines = []
    print("Beginning file reading...")
    for file in file_list:
        week = file.split('\\')[2].split('_')[1] + "-" + file.split('\\')[2].split('_')[2] + "-" + file.split('\\')[2].split('_')[3]
        time = int(t.mktime(t.strptime(week, '%Y-%m-%d')))
        obs = file.split('\\')[1]
        channel = file.split('\\')[3]
        numsiglines = len(sig_lines)

        #Find out which line belongs to which run, based on time.
        if int(file.split('\\')[2].split('_')[1]) <= 2019 and int(file.split('\\')[2].split('_')[2]) < 4:
            run = 'ER14' #The experimental run before O3 began took place between 2019-03-01 and 2019-04-01
        elif (int(file.split('\\')[2].split('_')[1]) > 2019) or (int(file.split('\\')[2].split('_')[1]) >= 2019 and int(file.split('\\')[2].split('_')[2]) >= 11):
            run = 'O3B' #The second part of the O3 observing run took place between 2019-11-01 and 2020-03-28
        else:
            run = 'O3A' #The first part of the O3 observing run took place between ER14 and O3B

        if verbose:
            print("Currently working with file: " + file.split('\\')[4] + " for channel " + channel + " in week " + week + "...")

        data = open(file, "r")
        for line in data:
            currline = line.split(' ') #Splits read line into frequency (index 0) and associated coherence (index 1)
            if currline == ['']:
                break
            if (currline[0].split('e')[1] == "+00"): #If the frequency isn't altered by the scientific notation after it... (i.e. 5*10^0)
                freq = float(currline[0].split('e')[0]) #Splits frequency XXXXe+00 into XXXX and e+00, then stores XXXX as frequency
            else: #Else...
                freq = float(currline[0].split('e')[0]) * (10 ** float(currline[0].split('e')[1]))
            freq = np.round(freq, 6)

            coh = float(currline[1]) #yStoring the coherence is... simpler.

            if coh > threshold and coh < 1: #Eliminates coherences below the threshold and extraneous coherences above 1 (with fscan, this shouldn't be an issue)
                sig_lines.append((freq, coh, channel, time, obs, run))
        if verbose:
            print("Moving to next file. Found " + str(len(sig_lines) - numsiglines) + " significant lines in file. Threshold is: " + str(threshold))
    
        if len(sig_lines) > chunksize:
            if verbose:
                print("\nList length exceeds chunk width. Moving currently stored lines into a temp file.")
            maketemp(sig_lines, tempnum)
            tempnum = tempnum + 1

def maketemp(sig_lines, num):
    #Creates a file containing a small selection of line objects

    tempname = "temp/chunk" + str(num) + ".lft"
    tempfile = open(tempname, "w")
    lineswritten = 0 #Counting variable
    for l in sig_lines:
        tempfile.write(str(l) + "\n")
        lineswritten = lineswritten + 1
    tempfile.close()
    sig_lines.clear()

    if verbosity:
        print("Temporary file " + tempname + " containing " + str(lineswritten) + " lines written to temp directory.\n")

def populate(verbosity):
    #A problem that arose as we neared production: We can't commit large (>3000000, at least) chunks to the database all at once.
    #To solve this, we cut the speed of the process (which is fine, because this program runs once) by populating the database in small chunks.
    #These chunks are stored in a 'temp' directory, and are read and stored one by one.
    
    totalchunks = [] #An array of numbers which dictates the order of the temp files that get pushed to database.
    totalcls = 0 #A counting variable for total lines committed
    sig_lines = [] #Create empty sig_lines list for line objects to be stored in
    tempname = "temp/chunk1.lft" #Default file name for chunk

    for files in os.walk(rootdir + "/temp"): #Get number of total chunks
        for file in files:
            templist = file
    
    for f in templist:
        totalchunks.append(int(f.strip("chunk.lft")))

    totalchunks.sort() #Sorts list numerically for easier time in for loop

    print(str(len(totalchunks)) + " chunk(s) will be used.")

    for chunk in totalchunks: #For the number of chunks necessary...
        tempname = "temp/chunk" + str(chunk) + ".lft"
        commitedlines = 0 #A counting variable
        tempfile = open(tempname, "r") #Reads chunk file in temp, stores lines in list
        for l in tempfile.readlines():
            sig_lines.append(eval(l))
        tempfile.close() #Closes file
        if len(sig_lines) == 0: #If there's no lines to look at, commit what we have 
            print("End of line list reached.")
            break
        while len(sig_lines) != 0:
            freq, coh, channel, time, obs, run = sig_lines[0] #Get first line in sig_lines list
            line = Line(freq=freq, coh=coh, time=time, run=run, channel=channel, obs=obs) #Create the line object from pertinent information
            db.session.add(line) #Add line to DB session
            sig_lines.pop(0) #Pop line off of list
            commitedlines = commitedlines + 1 #Count the added line
            totalcls = totalcls + 1

        db.session.commit() #When a chunk of chunksize lines is fully created, we push that small commit to the database.
        os.remove(tempname) #Deletes file once all lines are committed
        if verbosity:
            print("[" + tempname.strip("temp/chunk.lft") + ", " + str(totalcls) + "] Chunk committed, moving onto next chunk.")

    return totalcls

print("Running...")
#IMPORTANT: Put 'rootdir' as the main folder of this program, or else the database will not populate.
rootdir = '<MAIN FOLDER HERE>' #This root directory will look different on every machine.
threshold = 0.00 #Lines with coherences below this threshold will be ignored
chunksize = 50 #Width of chunks pushed to database

#Prompt user to see whether init should run with extra verbosity or not
verbosity = True
gate = True
while gate:
    userInput = input("Run init.py with extra verbosity? (Y/N): ")
    if userInput.lower() == "y":
        gate = False
    elif userInput.lower() == "n":
        verbosity = False
        gate = False
    else:
        print("Invalid character.")

#Check if temp directory exists
save_exists = False
for dirs in os.listdir(rootdir):
    if dirs == "temp":
        save_exists = True
        break

#Generate line list to commit to database. If a temp directory exists, pull sig lines from there as built into populate(). If not, read data directory.
if not save_exists:
    siglines = skim(verbosity)
    print("Beginning commitment of significant lines to the database.")
    del siglines #We no longer need this list.
else:
    print("Resuming partial commitment.")

totallines = populate(verbosity)
print("Finished commitment of " + str(totallines) + " lines to the database.")

#Check if temp directory exists again for removal.
for dirs in os.listdir(rootdir):
    if dirs == "temp":
        save_exists = True
        break

if save_exists:
    os.rmdir("temp") #Discards temp directory

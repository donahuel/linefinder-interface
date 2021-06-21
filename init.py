#This file populates a SQLite database with information about various lines
#Authors: Larry Donahue, Malachy Bloom, Michael Yang, Vincent He

from app import db, Line
import numpy as np
import os
import math as m

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
                
    sig_lines = []
    print("Beginning file reading...")
    for file in file_list:
        week = file.split('\\')[2].split('_')[1] + "-" + file.split('\\')[2].split('_')[2] + "-" + file.split('\\')[2].split('_')[3]
        obs = file.split('\\')[1]
        channel = file.split('\\')[3]
        numsiglines = len(sig_lines)

        if verbose:
            print("Currently working with file: " + file.split('\\')[4] + " for channel " + channel + " in week " + week + "...")

        data = open(file, "r")
        for line in data:
            currline = data.readline().split(' ') #Splits read line into frequency (index 0) and associated coherence (index 1)
            if currline == ['']:
                break
            if (currline[0].split('e')[1] == "+00"): #If the frequency isn't altered by the scientific notation after it... (i.e. 5*10^0)
                freq = float(currline[0].split('e')[0]) #Splits frequency XXXXe+00 into XXXX and e+00, then stores XXXX as frequency
            else: #Else...
                freq = float(currline[0].split('e')[0]) * (10 ** float(currline[0].split('e')[1]))
            freq = np.round(freq, 6)

            coh = float(currline[1]) #yStoring the coherence is... simpler.

            if coh > threshold and coh < 1: #Eliminates coherences below the threshold and extraneous coherences above 1 (with fscan, this shouldn't be an issue)
                sig_lines.append((freq, coh, channel, week, obs))
        if verbose:
            print("Moving to next file. Found " + str(len(sig_lines) - numsiglines) + " significant lines in file. Threshold is: " + str(threshold))

    return sig_lines

def maketemp(sig_lines, verbosity):
    #Creates a directory that temporarily houses line objects in text files
    os.mkdir("temp") #Creates directory. This directory should not exist at this point.
    totalchunks = m.ceil(len(sig_lines)/chunksize) #Total number of chunks needed to push to the database.

    print(str(totalchunks) + " temp files will be created.")

    for chunk in range(1, totalchunks+1): #For the number of chunks necessary...
        tempname = "temp/chunk" + str(chunk) + ".lft"
        tempfile = open(tempname, "w")
        lineswritten = 0 #Counting variable
        for l in sig_lines[0:chunksize]:
            tempfile.write(str(l) + "\n")
            sig_lines.pop(0)
            lineswritten = lineswritten + 1
        tempfile.close()
        if verbosity:
            print("Temporary file " + tempname + " containing " + str(lineswritten) + " lines written to temp directory.")
        if len(sig_lines) == 0: #If there's no lines to look at, commit what we have 
            print("End of line list reached.")
            break

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
        os.remove(tempname) #Deletes file once all lines are committed
        if len(sig_lines) == 0: #If there's no lines to look at, commit what we have 
            print("End of line list reached.")
            break
        while commitedlines <= chunksize:
            freq, coh, channel, week, obs = sig_lines[0] #Get first line in sig_lines list
            line = Line(freq=freq, coh=coh, week=week, run=run, channel=channel, obs=obs) #Create the line object from pertinent information
            db.session.add(line) #Add line to DB session
            sig_lines.pop(0) #Pop line off of list
            commitedlines = commitedlines + 1 #Count the added line
            totalcls = totalcls + 1
            if len(sig_lines) == 0: #If there's no lines to look at, break out of loop and go back to for loop
                break
        db.session.commit() #When a chunk of chunksize lines is fully created, we push that small commit to the database.
        if verbosity:
            print("[" + str(m.ceil(totalcls/chunksize)) + ", " + str(totalcls) + "] Chunk committed, moving onto next chunk.")

    return totalcls

print("Running...")
#IMPORTANT: Put 'rootdir' as the main folder of this program, or else the database will not populate.
rootdir = 'C:/Users/Scraf/Downloads/LFI-Main' #This root directory will look different on every machine.
run = 'O3B'
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
    print("All files read. Beginning creation of temp directory.")
    maketemp(siglines, verbosity)
    print("temp directory created. Beginning commitment of " + str(len(siglines)) + " significant lines to the database.")
    siglines.clear() #We no longer need this list.

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

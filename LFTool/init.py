##This file populates a SQLite database with information about various lines
#Authors: Vincent He, Larry Donahue

from app import db, Line
import numpy as np
import os
import math as m

def skim(verbose):
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

def populate(sig_lines, verbosity):
    #A problem that arose as we neared production: We can't commit large (>3000000, at least) chunks to the database all at once.
    #To solve this, we cut the speed of the process (which is fine, because this program runs once) by populating the database in small chunks.
    
    chunksize = 50 #Width of chunks pushed to database
    totalchunks = m.ceil(len(sig_lines)/chunksize) #Total number of chunks needed to push to the database.
    totalcls = 0 #A counting variable for total lines committed
    savefile = open("partialcom.txt", "w") #Creates an intermediate 'save' file for line objects to be stored in, in the event of a crash while the database is populating
    savefile.close()

    print(str(totalchunks) + " chunk(s) will be used.")

    for chunk in range(0, totalchunks+1): #For the number of chunks necessary...
        commitedlines = 0 #A counting variable
        savefile = open("partialcom.txt", "w") #Writes remaining lines to commit to the save file
        for l in sig_lines:
            savefile.write(str(l) + "&")
        savefile.close()
        if len(sig_lines) == 0: #If there's no lines to look at, commit what we have 
            print("End of line list reached.")
            break
        while commitedlines < chunksize:
            freq, coh, channel, week, obs = sig_lines[0] #Get first line in sig_lines list 
            line = Line(freq=freq, coh=coh, week=week, run=run, channel=channel, obs=obs) #Create the line object from pertinent information
            db.session.add(line) #Add line to DB session
            sig_lines.pop(0) #Pop line off of list
            commitedlines = commitedlines + 1 #Count the added line
            totalcls = totalcls + 1
            if len(sig_lines) == 0: #If there's no lines to look at, break out of loop and go back to for
                break
        db.session.commit() #When a chunk of chunksize lines is fully created, we push that small commit to the database.
        if verbosity:
            print("[" + str(m.ceil(totalcls/chunksize)) + ", " + str(totalcls) + "] Chunk committed, moving onto next chunk.")

    return totalcls

print("Running...")
#IMPORTANT: Put 'rootdir' as the main folder of this program, or else the database will not populate.
rootdir = '<MAIN FOLDER HERE>' #This root directory will look different on every machine.
run = 'O3B'
threshold = 0.00 #Lines with coherences below this threshold will be ignored

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

#Check if partial save file exists
save_exists = False
for file in os.listdir(rootdir):
    if file == "partialcom.txt":
        save_exists = True

#Generate line list to commit to database. If a save file exists, pull sig lines from there. If not, read data directory.
if save_exists:
    savefile = open("partialcom.txt", "r") #Opens save file
    siglinestrs = savefile.read().split("&") #Splits save file into constituent line objects
    siglinestrs.pop() #Gets rid of trailing empty line object
    siglines = []
    savefile.close()
    for l in siglinestrs: #Populates list with line objects found in file
        line = eval(l) #Turns "(freq, coh, chan, week, obs)" to (freq, coh, chan, week, obs)
        siglines.append(line)
    print("Save file read. Resuming partial commitment of " + str(len(siglines)) + " significant lines to the database.")
else:
    siglines = skim(verbosity)
    print("All files read. Beginning commitment of " + str(len(siglines)) + " significant lines to the database.")

totallines = populate(siglines, verbosity)
print("Finished commitment of " + str(totallines) + " lines to the database.")
if save_exists:
    os.remove("partialcom.txt") #Removes save file at end of successful commitment

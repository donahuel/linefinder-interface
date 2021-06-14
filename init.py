##This file populates a SQLite database with information about various lines
#Authors: Larry Donahue, Vincent He, Malachy Bloom, Michael Yang

def main():
    from app import db, Line
    import numpy as np
    import os
    db.drop_all()
    db.create_all()

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
            print("Invalid character. \n")        

    run = 'O3B'
    #IMPORTANT: Put 'rootdir' as the data folder within this program, or else the database will not populate.
    rootdir = 'C:/Users/Scraf/Downloads/LFI-Main/data' #This root directory will look different on every machine.
    file_list = []
    for subdir, dirs, files in os.walk(rootdir):
        for file in files:
            if file.endswith('.txt'):
                filepath = os.path.join(subdir, file)
                file_list.append(filepath)
                
    sig_lines = []
    print("Beginning file reading...")
    for file in file_list:
        week = file.split('\\')[2].split('_')[1] + "-" + file.split('\\')[2].split('_')[2] + "-" + file.split('\\')[2].split('_')[3]
        obs = file.split('\\')[4].split('_')[5]
        channel = file.split('\\')[3]
        numsiglines = len(sig_lines)

        if verbosity:
            print("Currently working with file: " + file.split('\\')[4] + " for channel " + channel + " in week " + week + "...")

        data = open(file, "r")
        for line in data:
            currline = data.readline().split(' ') #Splits read line into frequency (index 0) and associated coherence (index 1)
            if currline == ['']: #Prevents empty 'lines' from stopping code
                break
            if (currline[0].split('e')[1] == "+00"): #If the frequency isn't altered by the scientific notation after it... (i.e. 5*10^0)
                freq = float(currline[0].split('e')[0]) #Splits frequency XXXXe+00 into XXXX and e+00, then stores XXXX as frequency
            else: #Else...
                freq = float(currline[0].split('e')[0]) * (10 ** float(currline[0].split('e')[1]))
            freq = np.round(freq, 6)

            coh = float(currline[1]) #Storing the coherence is... simpler.

            threshold = 0.05 #Threshold for coherence. Coherences below this value are not stored as significant lines (or at all)
            if coh > threshold and coh < 1: #Eliminates coherences below the threshold and extraneous coherences above 1 (with fscan, this shouldn't be an issue)
                sig_lines.append((freq, coh, channel, week))
        if verbosity:
            print("Moving to next file. Found " + str(len(sig_lines) - numsiglines) + " significant lines in file. Threshold is: " + str(threshold))

    print("All files read. Commiting " + str(len(sig_lines)) + " significant lines to the database...")
    for sig_line in sig_lines: #Commits significant lines to database
        freq, coh, channel, week = sig_line
        line=Line(freq=freq, coh=coh, week=week, run=run, channel=channel, obs=obs)
        db.session.add(line)

    db.session.commit() #Adds the changes
    print("Committed " + str(len(sig_lines)) + " significant lines to the database.")
print("Running...")
main()


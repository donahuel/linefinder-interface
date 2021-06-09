#This file populates a SQLite database with information about various lines
#Authors: Larry Donahue, Malachy Bloom, Michael Yang, Vincent He

def main():
    from app import db, Line
    import numpy as np
    import os
    db.drop_all()
    db.create_all()

    run = 'O3B'
    #IMPORTANT: Put 'rootdir' as the data folder within this program, or else the database will not populate.
    rootdir = '/home/donahuel/LFTool/data' #This root directory will look different on every machine.
    file_list = []
    print(os.walk(rootdir))
    for subdir, dirs, files in os.walk(rootdir):
        print(subdir)
        for file in files:
            print(file)
            if file.endswith('.txt'):
                filepath = os.path.join(subdir, file)
                file_list.append(filepath)

    sig_lines = []
    for file in file_list:
        week = file.split('/')[6].split('_')[1] + "-" + file.split('/')[6].split('_')[2] + "-" + file.split('/')[6].split('_')[3]
        obs = file.split('/')[5]
        channel = file.split('/')[7]
        numsiglines = len(sig_lines)

        print("Currently working with file: " + file.split('/')[8] + " for channel " + channel + " in week " + week + "...")

        data = open(file, "r")
        for line in data:
            currline = data.readline().split(' ') #Splits read line into frequency (index 0) and associated coherence (index 1)
            if currline == ['']: #Empty case, just passes line through
                pass
            else:
                if (currline[0].split('e')[1] == "+00"): #If the frequency isn't altered by the scientific notation after it... (i.e. 5*10^0)
                    freq = float(currline[0].split('e')[0]) #Splits frequency XXXXe+00 into XXXX and e+00, then stores XXXX as frequency
                else: #Else...
                    freq = float(currline[0].split('e')[0]) * (10 ** float(currline[0].split('e')[1]))
                freq = np.round(freq, 6)

                coh = float(currline[1]) #Storing the coherence is... simpler.

                threshold = 0.95 #Threshold for coherence. Coherences below this value are not stored as significant lines (or at all)
                if coh > threshold and coh < 1: #Eliminates coherences below the threshold and extraneous coherences above 1 (with fscan, this shouldn't be an issue)
                    sig_lines.append((freq, coh, channel, week))
        print("Moving to next file. Found " + str(len(sig_lines) - numsiglines) + " significant lines in file. Threshold is: " + str(threshold))

    print("There is no next file. Commiting " + str(len(sig_lines)) + " significant lines to the database...")
    for sig_line in sig_lines:
        freq, coh, channel, week = sig_line
        line=Line(freq=freq, coh=coh, week=week, run=run, channel=channel, obs=obs)
        db.session.add(line)

    db.session.commit()
    print("Committed " + str(len(sig_lines)) + " significant lines to the database.")
print("Running init.py...")
main()



# Plot Renamer
# Author: Larry Donahue
# This program shortens the name of fscan plot files for ease of use for the Linefinder Interface located at https://github.com/donahuel/linefinder-interface.

import os
import subprocess

def renameFiles(rootdir):

        #Counting variable
        filecount = 0

        #For loop that runs through directory:
        for subdir, dirs, files, in os.walk(rootdir): #Walk through every directory/subdirectory within the root directory
                print("Current directory: " + subdir) #Prints current directory
                for file in files:
                        fileparts = file.split("_")
                        newname = fileparts[0] + "_" + fileparts[1] + "_" + fileparts[2] + ".png" #We only want the first few parts of the file name to remain
                        subprocess.call(["mv", subdir + "/" + file, subdir + "/" + newname]) #Do the renaming
                        print("File " + file + " renamed to " + newname)
                        filecount = filecount + 1

        return filecount

def renameDirs(rootdir):

        #Counting variable
        dircount = 0

        #For loop that runs through directory:
        for subdir, dirs in os.walk(rootdir):

                print("Current directory: " + subdir) #Prints current directory
                subdirparts = subdir.split("/") #Splits current directory into parts
                if subdirparts[-1].split("_")[0] == "fscans": #We only want to rename the fscans_... directories.
                        newname = "plots_" + subdirparts[-1].split("_")[1] + "_" + subdirparts[-1].split("_")[2] + "_" + subdirparts[-1].split("_")[3] #Generate new name
                        subprocess.call(["mv", subdir, "/" + subdirparts[1] + "/" + subdirparts[2] + "/" + subdirparts[3] + "/" + subdirparts[4] + "/" + subdirparts[5] + "/" + newname) #Carry out the renaming
                print("Directory " + subdirparts[-1] + " renamed to " + newname)
                dircount = dircount + 1

        return dircount

rootdir = "/home/larry.donahue/plots" #Define root directory in which thigns will be renamed
print("Plot Renamer opened. Beginning renaming.")
numfiles = renameFiles()
print("Renamed " + str(numfiles) + " coherence plot files.")
print("Beginning directory renaming.")
numdirs = renameDirs()
print("Renamed " + str(numdirs) " plot directories.")

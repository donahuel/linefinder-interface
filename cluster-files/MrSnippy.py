# Mr. Snippy
# Author: Larry Donahue
# This program aims to trim long-term coherence data collected by CoherenceGrab.py. This reduces file sizes and eliminates insignificant coherences below a certain threshold.
# This program is intended for use on the LIGO clusters, and lives there.
# This program is dedicated to former MLB pitcher, Randy Johnson, and his slider, Mr. Snappy.

import os
import subprocess

def snip():
        #Define root directory to snip data from
        rootdir = "/home/larry.donahue/H1"

        #Counting variables
        storedlines = 0
        workingDir = ""
        threshold = 0.95

        #For loop that runs through directory
        for subdir, dirs, files in os.walk(rootdir):
                #Helpful print messages
                if len(subdir.split("/")) == 10:
                        print("Done in directory " + workingDir + " | " + str(storedlines) + " lines stored so far. Estimated database size: " + str(storedlines * 0.06) + "KB.")
                        print("Currently working in directory: " + subdir.split("/")[9])
                        workingDir = subdir.split("/")[9]
                #When we find a file...
                for file in files:
                        sigLines = [] #Significant lines to be written to new file
                        filestoredlines = 0 #Counting variable
                        data = open(subdir + "/" + file, "r") #Open first file
                        for line in data:
                                #If the coherence is greater than the threshold, the line gets stored
                                if float(line.split()[1]) > threshold:
                                        sigLines.append(line)
                                        storedlines = storedlines + 1
                                        filestoredlines = filestoredlines + 1
                        data.close() #Close first file
                        os.remove(subdir + "/" + file) #Delete first file
                        #Open and create new file for significant coherences
                        newData = open(subdir + "/" + file, "w")
                        for sigLine in sigLines:
                                newData.writelines(sigLine) #Write lines to new file one by one
                        print("Moving onto new file. " + str(storedlines) + " have been stored so far, with this file contributing " + str(filestoredlines) + ".")

print("Readying Mr. Snippy. Going into directory...")
snip()

#This file populates a SQLite database with information about various lines
#Authors: Vincent He, Larry Donahue

def main():
    from app import db, Line
    import numpy as np
    from scipy.io import loadmat
    import os
    db.drop_all()
    db.create_all()

    run = 'O2'
    #IMPORTANT: Put 'rootdir' as the data folder within this program, or else the database will not populate.
    rootdir = '/Users/Scraf/Downloads/test_program_normalized/test_program_normalized/data'
    file_list = []
    for subdir, dirs, files in os.walk(rootdir):
        for file in files:
            if file.endswith('.mat'):
                filepath = os.path.join(subdir, file)
                file_list.append(filepath)
                
    
    for file in file_list:
        week = file.split('/')[6].split('_')[2]

        channel = file.split('/')[6].replace('_DQ_data.mat','').split('\\')[2]

        data = loadmat(file)
        freqs = list(data.get('freqs').flatten())
        cohs = list(data.get('coh').flatten())
        print(len(freqs),len(cohs))
        sig_lines = []
        threshold = 0.95
        for coh in cohs:
            if coh>threshold and coh<1:
                sig_freq = freqs[cohs.index(coh)]
                sig_lines.append((sig_freq, coh))

        for sig_line in sig_lines:
            freq, coh = sig_line
            line=Line(freq=freq, coh=coh, week=week, run=run, channel=channel)
            db.session.add(line)

    db.session.commit()
print("Running...")
main()


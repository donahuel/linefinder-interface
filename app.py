#This file searches the database populated by init.py and displays the results on a webpage.
#Authors: Vincent He, Larry Donahue, Malachy Bloom, Michael Yang

from flask import Flask, render_template, url_for, flash, request, redirect, Response
from flask_sqlalchemy import SQLAlchemy
from wtforms import Form, StringField, validators
import csv
import numbers

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///line_finder.db'
db = SQLAlchemy(app)
    
#The database itself, this is the class containing information about each row
class Line(db.Model):
    id = db.Column(db.Integer, primary_key=True) #Unique ID for each line
    run = db.Column(db.String(10)) #Run for each line
    obs = db.Column(db.String(10)) #Observatory for each line
    week = db.Column(db.String(50)) #Week for each line (e.g. 1175904015)
    channel = db.Column(db.String(50)) #Channel for each line (e.g. L1_PEM-CS_MAG_LVEA_VERTEX_Z)
    freq = db.Column(db.Float) #Frequency for each line
    coh = db.Column(db.Float) #Coherence for each line
   
    def __repr__(self):
        return f"{self.run},{self.obs},{self.week},{self.channel},{self.freq},{self.coh}"
    
#Search form
class SearchForm(Form):
    run = StringField('Run:')
    obs = StringField('Observatory:')
    stDate = StringField('Start Date:')
    endDate = StringField('End Date:')
    channel = StringField('Channel:')
    frequb = StringField('Frequency upper bound:')
    freqlb = StringField('Frequency lower bound:')
    cohub = StringField('Coherence upper bound:')
    cohlb = StringField('Coherence lower bound:')

dLines = []
    
@app.route("/", methods=['GET', 'POST'])
def index():
    searchForm = SearchForm(request.form)
    lines = Line.query.all() #Set of all lines which will be cut by the searches  

    if request.method == 'POST' and searchForm.validate():

        dlines = [] #Desired lines based on search query
        sortedBy = [] #List used to sort

        #Assigning defaults to values.
        searchForm.freqlb.data == "0"
        searchForm.cohlb.data == "0"

        def is_float(s):
            try:
                float(s)
                return True
            except ValueError:
                return False
        
        def is_int(s):
            try:
                int(s)
                return True
            except ValueError:
                return False

        #Edge cases that the form doesn't like. Takes it in and spits back the form with an error message attached.
        if len(searchForm.frequb.data) != 0:
            if is_float(searchForm.frequb.data) == False and is_int(searchForm.frequb.data) == False:
                return render_template('lineform.html', form=searchForm, errormessage="Error: Bounds of frequency must be a number.")
        if len(searchForm.freqlb.data) != 0:
            if is_float(searchForm.freqlb.data) == False and is_int(searchForm.freqlb.data) == False:
                return render_template('lineform.html', form=searchForm, errormessage="Error: Bounds of frequency must be a number.")
        if len(searchForm.frequb.data) != 0 and len(searchForm.freqlb.data) != 0: #If frequency is bounded on both sides, UB < LB cannot be true
            if float(searchForm.frequb.data) < float(searchForm.freqlb.data):
                return render_template('lineform.html', form=searchForm, errormessage="Error: Lower bound of frequency must be less than or equal to upper bound.")
        
        if len(searchForm.cohub.data) != 0:
            if is_float(searchForm.cohub.data) == False and is_int(searchForm.cohub.data) == False:
                return render_template('lineform.html', form=searchForm, errormessage="Error: Bounds of coherence must be a number.")
        if len(searchForm.cohlb.data) != 0:
            if is_float(searchForm.cohlb.data) == False and is_int(searchForm.cohlb.data) == False:
                return render_template('lineform.html', form=searchForm, errormessage="Error: Bounds of coherence must be a number.")
        if len(searchForm.cohub.data) != 0 and len(searchForm.cohlb.data) != 0: #If coherence is bounded on both ends, LB > UB cannot be true
            if float(searchForm.cohub.data) < float(searchForm.cohlb.data):
                return render_template('lineform.html', form=searchForm, errormessage="Error: Lower bound of coherence must be less than or equal to upper bound.")
        

        stringListSortedBy = []
        id = 0    
            
        for l in lines: #For each line...
            #Set checks for each field to false
            rnCheck = False
            yrCheck = False
            monthCheck = False
            dayCheck = False
            obCheck = False
            chCheck = False
            fqCheck = False
            coCheck = False
            
            if len(searchForm.endDate.data) == 0: # if End Date field is empty, there is effectively no bound on end date
                endYear = str(9999)
                endMonth = str(99)
                endDay = str(99)
            else: # slice the string from user input to find the respective year, month, and day
                endYear = searchForm.endDate.data[:4]
                endMonth = searchForm.endDate.data[5:7]
                endDay = searchForm.endDate.data[8:]

            if len(searchForm.stDate.data) == 0: # if Start Date field is empty, there is effectively no bound on start date
                startYear = str(0)
                startMonth = str(0)
                startDay = str(0)
            else: # slice the string from user input to find the respective year, month, and day
                startYear = searchForm.stDate.data[:4]
                startMonth = searchForm.stDate.data[5:7]
                startDay = searchForm.stDate.data[8:]

            # slice the week of the line object into year, month, and day components
            year = l.week[:4]
            month = l.week[5:7]
            day = l.week[8:]

            if searchForm.run.data in l.run: #If run matches search query
                rnCheck = True #...pass run check.
            if rnCheck:    
                if request.form.get('H1') == l.obs or request.form.get('L1') == l.obs or (request.form.get('H1') == request.form.get('L1') == None):
                    obCheck = True
            if obCheck: #If run check is passed...
                if (startYear < year and endYear > year): #...and year is between startYear and endYear search query...
                    yrCheck = True #...pass year range check.
                    monthCheck = True #...pass month range check.
                    dayCheck = True #...pass day range check.
                elif (startYear == year or endYear == year): #...and year is the same as either startYear or endYear search query...
                    yrCheck = True #...pass year range check.
            if yrCheck: #If year range check is passed...
                if (startMonth < month and endMonth > month): #...and month range matches search query...
                    monthCheck = True #...pass month range check.
                    dayCheck = True
                elif (startMonth == month or endMonth == month):
                    monthCheck = True
            if monthCheck: #If month range check is passed...
                if (startDay <= day and endDay >= day): #...and day range matches search query...
                    dayCheck = True #...pass day range check.
            if dayCheck: #If day range check is passed...
                if searchForm.channel.data in l.channel or searchForm.channel.data.upper() in l.channel or len(searchForm.channel.data) == 0: #...and channel matches search query OR channel field is empty...
                    chCheck = True
            if chCheck: #If channel (and run, week) checks are passed...
                if len(searchForm.frequb.data) == 0 and len(searchForm.freqlb.data) != 0: #...we see if the search query frequency has a lower, but no upper, bound. If so...
                    if float(searchForm.freqlb.data) < l.freq: #...we check if the line has a greater frequency than the lower bound...
                        fqCheck = True #...if so, pass frequency check.
                elif len(searchForm.freqlb.data) == 0 and len(searchForm.frequb.data) != 0: #...we see if the search query frequency has an upper, but no lower, bound. If so...
                    if float(searchForm.frequb.data) > l.freq: #...we check if the line has a lesser frequency than the upper bound...
                        fqCheck = True #...if so, pass frequency check.
                elif len(searchForm.freqlb.data) != 0 and len(searchForm.frequb.data) != 0: #...we see if the search query is bounded on both ends. If so...
                    if float(searchForm.freqlb.data) < l.freq and float(searchForm.frequb.data) > l.freq: #...we check if the line's frequency is within bounds...
                        fqCheck = True #...if so, pass frequency check.
                else: #...by the first 3 mutually exclusive statements passing, this means both frequency queries are blank. And thus...
                    fqCheck = True #...the frequency check passes.
            if fqCheck: #If frequency (and run, week, channel) checks are passed...
                if len(searchForm.cohub.data) == 0 and len(searchForm.cohlb.data) != 0: #...we see if the search query coherence has a lower, but no upper, bound. If so...
                    if float(searchForm.cohlb.data) < l.coh: #...we check if the line has a greater coherence than the lower bound...
                        coCheck = True #...if so, pass coherence check.
                elif len(searchForm.cohlb.data) == 0 and len(searchForm.cohub.data) != 0: #...we see if the search query coherence has an upper, but no lower, bound. If so...
                    if float(searchForm.cohub.data) > l.coh: #...we check if the line has a lesser coherence than the upper bound...
                        coCheck = True #...if so, pass coherence check.
                elif len(searchForm.cohlb.data) != 0 and len(searchForm.cohub.data) != 0: #...we see if the search query is bounded on both ends. If so...
                    if float(searchForm.cohlb.data) < l.coh and float(searchForm.cohub.data) > l.coh: #...we check if the line's coherence is within bounds...
                        coCheck = True #...if so, pass coherence check.
                else: #...by the first 3 mutually exclusive statements passing, this means both coherence queries are blank. And thus...
                    coCheck = True #...the coherence check passes.
            if coCheck: #If all checks are passed...
                dlines.append(l) #Add line to desired lines\ 
                
                for lines in dlines:
                    subList = []
                    stringLine = str(lines)
                    subList.append(stringLine.split(","))

                for i in subList:
                    i[4] = float(i[4])
                    i[5] = float(i[5])
                
                    sortedBy = sorted(subList, key = lambda x: x[4])
            
            for i, lines in enumerate(sortedBy):
                id += 1
                newDict = {"id" : id , "run" : lines[0], "obs" : lines[1], "week" : lines[2], "channel" : lines[3], "freq" : lines[4], "coh" : lines[5]}
                stringListSortedBy.append(newDict)
            
        #get the value from the dropdown menu, sort by that value.
        sortMenu = request.form.get('sorting')
        
        if request.form.get('order') == "ascending":
            orderMenu = False
        else:
            orderMenu = True
        
        stringListSortedBy = sorted(stringListSortedBy, key = lambda x: x[sortMenu], reverse = orderMenu)
                
        global run           #Global variables used for csv file
        run = searchForm.run.data
        if run == '':
            run = 'All'
            
        global obs
        if (request.form.get('H1') == 'H1' and request.form.get('L1') == 'L1') or request.form.get('H1') == request.form.get('L1') == None:
            obs = 'H1 and L1'
        elif request.form.get('H1') == None:
            obs = 'L1'
        elif request.form.get('L1') == None:
            obs = 'H1'

        global stTime
        stTime = searchForm.stDate.data
        if stTime == '':
            stTime = 'Start'
        global enTime
        enTime = searchForm.endDate.data
        if enTime == '':
            enTime = 'End'

        global channel
        channel = searchForm.channel.data
        if channel == '':
            channel = 'All'

        global freqLB
        freqLB = searchForm.freqlb.data
        if freqLB == '':
            freqLB = '0hz'
        global freqUB
        freqUB = searchForm.frequb.data
        if freqUB == '':
            freqUB = '2000hz'

        global cohLB
        cohLB = searchForm.cohlb.data
        if cohLB == '':
            cohLB = '0'
        global cohUB
        cohUB = searchForm.cohub.data
        if cohUB == '':
            cohUB = '1'

        global dLines
        dLines = dlines

        return render_template('lineresult.html', dlines=stringListSortedBy)

    if request.method == 'GET':
        return render_template('lineform.html', form=searchForm, errormessage="", helpmessage="", tries=1)

    else:
        "Something went wrong."


@app.route("/data.csv")
def getPlotCSV():

    csv = str('Run: ' + run + ',') + str('Observatory: ' + obs + ',') + str('Time Range: ' + stTime + ' to ' + enTime + ',') + str('Channel: ' + channel + ',') + str('Frequency: ' + freqLB + ' - ' + freqUB + ',') + str('Coherence: ' + cohLB + ' - ' + cohUB + ',') + '\n'
    
    
    for line in dLines:
        csv = csv + str(line) + '\n'
    csv = csv.encode()
    
    return Response(
        csv, 
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=myplot.csv"})


if __name__ == '__main__':
    app.run(debug=True)

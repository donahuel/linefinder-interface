#This file searches the database populated by init.py and displays the results on a webpage.
#Authors: Vincent He, Larry Donahue

from flask import Flask, render_template, url_for, flash, request, redirect, Response
from flask_sqlalchemy import SQLAlchemy
from wtforms import Form, StringField, validators
import csv

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///line_finder.db'
db = SQLAlchemy(app)
    
#The database itself, this is the class containing information about each row
class Line(db.Model):
    id = db.Column(db.Integer, primary_key=True) #Unique ID for each line
    run = db.Column(db.String(10)) #Run for each line
    week = db.Column(db.String(50)) #Week for each line (e.g. 1175904015)
    channel = db.Column(db.String(50)) #Channel for each line (e.g. L1_PEM-CS_MAG_LVEA_VERTEX_Z)
    freq = db.Column(db.Float) #Frequency for each line
    coh = db.Column(db.Float) #Coherence for each line
   
    def __repr__(self):
        return f"{self.run}/{self.week}/{self.channel}/{self.freq}/{self.coh}"
    
#Search form
class SearchForm(Form):
    run = StringField('Run:')
    week = StringField('Week:')
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

        #Assigning defaults to values.
        searchForm.freqlb.data == "0"
        searchForm.cohlb.data == "0"

        #Edge cases that the form doesn't like. Takes it in and spits back the form with an error message attached.
        if len(searchForm.frequb.data) != 0 and len(searchForm.freqlb.data) != 0: #If frequency is bounded on both sides, UB < LB cannot be true
            if float(searchForm.frequb.data) < float(searchForm.freqlb.data):
                return render_template('lineform.html', form=searchForm, errormessage="Error: Lower bound of frequency must be less than or equal to upper bound.")

        if len(searchForm.cohub.data) != 0 and len(searchForm.cohlb.data) != 0: #If coherence is bounded on both ends, LB > UB cannot be true
            if float(searchForm.cohub.data) < float(searchForm.cohlb.data):
                return render_template('lineform.html', form=searchForm, errormessage="Error: Lower bound of coherence must be less than or equal to upper bound.")

        stringListSortedBy = []
        id = 0    
            
        for l in lines: #For each line...
            #Set checks for each field to false
            rnCheck = False
            wkCheck = False
            chCheck = False
            fqCheck = False
            coCheck = False

            if searchForm.run.data in l.run or len(searchForm.run.data) == 0: #If run matches search query OR run field is empty (no run specified)...
                rnCheck = True #...pass run check.
            if rnCheck: #If run check is passed...
                if searchForm.week.data in l.week or len(searchForm.week.data) == 0: #...and week matches search query OR week field is empty...
                    wkCheck = True #...pass week check.
            if wkCheck: #If week check (and therefore run check) are passed...
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
                
                
                sortedBy = []
                
                for lines in dlines:
                    subList = []
                    stringLine = str(lines)
                    subList.append(stringLine.split("/"))

                for i in subList:
                    i[3] = float(i[3])
                    i[4] = float(i[4])
                
                    sortedBy = sorted(subList, key = lambda x: x[3])
            
            for i, lines in enumerate(sortedBy):
                id += 1
                newDict = {"id" : id , "run" : lines[0], "week" : lines[1], "channel" : lines[2], "freq" : lines[3], "coh" : lines[4]}
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

        global week
        week = searchForm.week.data
        if week == '':
            week = 'All'

        global channel
        channel = searchForm.channel.data
        if channel == '':
            channel = 'All'

        global freqLB
        freqLB = searchForm.freqlb.data
        if freqLB == '':
            freqLB = '0'
        global freqUB
        freqUB = searchForm.frequb.data
        if freqUB == '':
            freqUB = 'Highest'

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
    

    csv = str('Run: ' + run + ',') + str('Week: ' + week + ',') + str('Channel: ' + channel + ',') + str('Frequency: ' + freqLB + ' - ' + freqUB + ',') + str('Coherence: ' + cohLB + ' - ' + cohUB + ',') + '\n'
    
    
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

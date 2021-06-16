##This file produces a web interface which searches a database populated by init.py for line objects and displays the results on a webpage.
#Authors: Larry Donahue, Vincent He Malachy Bloom, Michael Yang

from flask import Flask, render_template, url_for, flash, request, redirect, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
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
    week = db.Column(db.String(50)) #Week for each line (e.g. 2017/01/01)
    channel = db.Column(db.String(50)) #Channel for each line (e.g. L1_PEM-CS_MAG_LVEA_VERTEX_Z)
    freq = db.Column(db.Float) #Frequency for each line
    coh = db.Column(db.Float) #Coherence for each line
   
    def __repr__(self):
        return f"{self.run},{self.obs},{self.week},{self.channel},{self.freq},{self.coh}"
    
#Search form fields
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

#Important lists we append to over the course of the code.
#dLines is the list of 'desired lines,' or lines that fit the search criterion.
#sortedBy is the list used to sort the desired lines
dLines = []
sortedBy = []
    
@app.route("/", methods=['GET', 'POST'])
def index():
    searchForm = SearchForm(request.form)

    if request.method == 'POST' and searchForm.validate():

        sortedBy.clear() #Clears sorted list in the event of repeated queries (prevents duplication of line objects)

        #The following blocks of code catch errors in user input in the date section.        
        if len(searchForm.stDate.data) != 0 and len(searchForm.stDate.data) != 10:
            return render_template('lineform.html', form=searchForm, errormessage="Error: Invalid date format.")
        if len(searchForm.endDate.data) != 0 and len(searchForm.endDate.data) != 10:
            return render_template('lineform.html', form=searchForm, errormessage="Error: Invalid date format.")
        
        if len(searchForm.stDate.data) == 10:
            if searchForm.stDate.data[4] != "/" or searchForm.stDate.data[7] != "/":
                return render_template('lineform.html', form=searchForm, errormessage="Error: Invalid date format.")
        if len(searchForm.endDate.data) == 10:
            if searchForm.endDate.data[4] != "/" or searchForm.endDate.data[7] != "/":
                return render_template('lineform.html', form=searchForm, errormessage="Error: Invalid date format.")

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

        #Assigning default values to fields. These are the values that will be altered by the search form data. The run and observatories' default values are automatically selected by the interface.
        searchParams = ["0000/01/01", "9999/12/31", "", -0.01, 9999, -0.01, 9.99]

        #Altering default values based on user-defined query. Run is not present due to the interface deciding the value automatically, and observatories' checkbox nature makes them work differently.
        if len(searchForm.stDate.data) != 0:
            searchParams[0] = searchForm.stDate.data
        if len(searchForm.endDate.data) != 0:
            searchParams[1] = searchForm.endDate.data
        if len(searchForm.channel.data) != 0:
            searchParams[2] = searchForm.channel.data
        if len(searchForm.freqlb.data) != 0:
            searchParams[3] = searchForm.freqlb.data
        if len(searchForm.frequb.data) != 0:
            searchParams[4] = searchForm.frequb.data
        if len(searchForm.cohlb.data) != 0:
            searchParams[5] = searchForm.cohlb.data
        if len(searchForm.cohub.data) != 0:
            searchParams[6] = searchForm.cohub.data

        print(searchForm.run.data, request.form.get('H1'), request.form.get('L1'), searchForm.stDate.data, searchForm.endDate.data, searchForm.channel.data, searchForm.freqlb.data, searchForm.frequb.data, searchForm.cohlb.data, searchForm.cohub.data)
        stringListSortedBy = [] #Generates array where sorted list is stored (and eventually printed from)
        id = 0 #A counting variable for the sorting dictionary, to be defined later
        
        #Set of lines which satisfy run, coherence, and frequency search criteria. This cuts down search results dramatically compared to starting with the entire database.
        lines = Line.query.filter(
            Line.run == searchForm.run.data,
            (searchParams[3] <= Line.freq) & (Line.freq <= searchParams[4]),
            (searchParams[5] <= Line.coh) & (Line.coh <= searchParams[6])
        ).limit(2500)
        print(lines)
        
        for l in lines: #For each line...
            if len(dLines) < 2500: #Makes sure dLines does not swell too big, prevents breaking of page
                #Set checks for each field to false
                yrCheck = False
                monthCheck = False
                dayCheck = False
                obCheck = False
                chCheck = False

                # Slice the weeks of the line object and both user queries into year, month, and day components
                year = l.week[:4]
                month = l.week[5:7]
                day = l.week[8:]
                startYear = searchParams[0][:4]
                startMonth = searchParams[0][5:7]
                startDay = searchParams[0][8:]
                endYear = searchParams[1][:4]
                endMonth = searchParams[1][5:7]
                endDay = searchParams[1][8:]

                if request.form.get('H1') == l.obs or request.form.get('L1') == l.obs or (request.form.get('H1') == request.form.get('L1') == None): #Check observatory selection
                    obCheck = True
                if obCheck: #If observatory check is passed...
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
                    dLines.append(l) #Add line to desired lines

        #Now that desired lines are generated, begin sorting
        subList = [] #Container for simplified dLines
        for l in dLines: #Converts line objects to lists of strings...
            lString = str(l)
            subList.append(lString.split(","))

        for l in subList: #...and floats. We then append these objects to the previously defined sortedBy list.
            l[4] = float(l[4])
            l[5] = float(l[5])
            sortedBy.append(l)

        #Generate pretty list that ends up getting displayed by enumerating over sorted list
        for i, lines in enumerate(sortedBy):
            id += 1
            newDict = {"id" : id , "run" : lines[0], "obs" : lines[1], "week" : lines[2], "channel" : lines[3], "freq" : lines[4], "coh" : lines[5]}
            stringListSortedBy.append(newDict)

        #Get the value from the dropdown menu, sort by that value.
        sortMenu = request.form.get('sorting')
        
        if request.form.get('order') == "ascending":
            orderMenu = False
        else:
            orderMenu = True
        
        stringListSortedBy = sorted(stringListSortedBy, key = lambda x: x[sortMenu], reverse = orderMenu)
                
        #Global variables used for .csv file
        global run
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
            freqUB = '2000Hz'

        global cohLB
        cohLB = searchForm.cohlb.data
        if cohLB == '':
            cohLB = '0'
        global cohUB
        cohUB = searchForm.cohub.data
        if cohUB == '':
            cohUB = '1'

        if len(dLines) == 2500:
            return render_template('lineresult.html', dlines=stringListSortedBy, warning="Line search limited to the first 2500 results found. Try confining bounds for a more specific search. Lines with coherences or frequencies outside the ranges shown here may exist.")

        if len(dLines) == 0:
            return render_template('lineresult.html', dlines=stringListSortedBy, warning="No lines found. Try loosening bounds for a more broad search.")
        
        else:
            return render_template('lineresult.html', dlines=stringListSortedBy, warning="")

    if request.method == 'GET':
        return render_template('lineform.html', form=searchForm, errormessage="", helpmessage="")

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

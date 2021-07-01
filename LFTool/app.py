#This file produces a web interface which searches a database populated by init.py for line objects and displays the results on a webpage.
#Authors: Larry Donahue, Vincent He Malachy Bloom, Michael Yang

from flask import Flask, render_template, request, Response, send_file
from flask_sqlalchemy import SQLAlchemy
from wtforms import Form, StringField
import csv
import time

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///line_finder.db'
db = SQLAlchemy(app)
    
#The database itself, this is the class containing information about each row
class weekly(db.Model): #Weekly coherences
    id = db.Column(db.Integer, primary_key=True) #Unique ID for each line
    run = db.Column(db.String(10), index=True) #Run for each line
    obs = db.Column(db.String(10)) #Observatory for each line
    time = db.Column(db.Integer, index=True) #Epoch timestamp for each line, that can be converted into a date (e.g. 1483228800, which can become 2017/01/01)
    channel = db.Column(db.String(50)) #Channel for each line (e.g. L1_PEM-CS_MAG_LVEA_VERTEX_Z)
    freq = db.Column(db.Float, index=True) #Frequency for each line
    coh = db.Column(db.Float, index=True) #Coherence for each line
   
    def __repr__(self):
        return f"W,{self.run},{self.obs},{self.time},{self.channel},{self.freq},{self.coh}"

class monthly(db.Model): #Monthly coherences. Identical to weekly coherences, with the important distinction of range that necessitates a new table/database model.
    id = db.Column(db.Integer, primary_key=True) #Unique ID for each line
    run = db.Column(db.String(10), index=True) #Run for each line
    obs = db.Column(db.String(10)) #Observatory for each line
    time = db.Column(db.Integer, index=True) #Epoch timestamp for each line, that can be converted into a date (e.g. 1483228800, which can become 2017/01/01)
    channel = db.Column(db.String(50)) #Channel for each line (e.g. L1_PEM-CS_MAG_LVEA_VERTEX_Z)
    freq = db.Column(db.Float, index=True) #Frequency for each line
    coh = db.Column(db.Float, index=True) #Coherence for each line
   
    def __repr__(self):
        return f"M,{self.run},{self.obs},{self.time},{self.channel},{self.freq},{self.coh}"
            
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

        dLines.clear() #Clears dLines list in the event of repeated queries (prevents duplication of line objects)
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
        searchParams = ["1970/01/01", "2050/12/31", "", -0.01, 9999, -0.01, 9.99]

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

        #Slice user inputted dates into their components
        startYear = searchParams[0][:4]
        startMonth = searchParams[0][5:7]
        startDay = searchParams[0][8:]
        endYear = searchParams[1][:4]
        endMonth = searchParams[1][5:7]
        endDay = searchParams[1][8:]

        #Convert user inputted dates into epoch timestamp
        sString = startYear + "-" + startMonth + "-" + startDay
        sDate = int(time.mktime(time.strptime(sString, '%Y-%m-%d')))
        eString = endYear + "-" + endMonth + "-" + endDay
        eDate = int(time.mktime(time.strptime(eString, '%Y-%m-%d')))

        stringListSortedBy = [] #Generates array where sorted list is stored (and eventually printed from)
        stringListSortedBy.clear() #Clears list in the event of repeated queries (prevents duplication of line objects)
        id = 0 #A counting variable for the sorting dictionary, to be defined later
        
        #Set of lines which satisfy run, obsrevatory, coherence, time, and frequency search criteria. This cuts down search results dramatically compared to starting with the entire database.
        #Depending on what time range is specified, we either look at weekly or monthly coherences.
    
        if request.form.get('range') == "Weekly" or request.form.get('range') == None:
            lines = weekly.query.filter(
                weekly.run == searchForm.run.data,
                weekly.obs == searchForm.obs.data,
                (searchParams[3] <= weekly.freq) & (weekly.freq <= searchParams[4]),
                (searchParams[5] <= weekly.coh) & (weekly.coh <= searchParams[6]),
                (sDate <= weekly.time) & (weekly.time <= eDate)
            ).limit(25000)
        if request.form.get('range') == "Monthly":
            lines = monthly.query.filter(
                monthly.run == searchForm.run.data,
                monthly.obs == searchForm.obs.data,
                (searchParams[3] <= monthly.freq) & (monthly.freq <= searchParams[4]),
                (searchParams[5] <= monthly.coh) & (monthly.coh <= searchParams[6]),
                (sDate <= monthly.time) & (monthly.time <= eDate)
            ).limit(25000)
        
        for l in lines: #For each line...
            if len(dLines) < 2500: #Makes sure dLines does not swell too big, prevents breaking of page
                #Set checks for each field to false
                chCheck = False #Channel

                if searchForm.channel.data in l.channel or searchForm.channel.data.upper() in l.channel or len(searchForm.channel.data) == 0: #and channel matches search query OR channel field is empty,
                    chCheck = True #pass the check.
                if chCheck: #If channel check is passed,
                    dLines.append(l) #add line to desired lines list.

        #Now that desired lines are generated, begin sorting
        subList = [] #Container for simplified dLines
        for l in dLines: #Converts line objects to lists of strings...
            lString = str(l)
            subList.append(lString.split(","))

        for l in subList: #...and floats. And convert epoch timestamp into human date. We then append these objects to the previously defined sortedBy list.
            l[3] = time.strftime('%Y-%m-%d', time.localtime(int(l[3])))
            l[5] = float(l[5])
            l[6] = float(l[6])
            sortedBy.append(l)

        #Generate pretty list that ends up getting displayed by enumerating over sorted list
        for i, lines in enumerate(sortedBy):
            id += 1
            newDict = {"id" : id , "run" : lines[1], "obs" : lines[2], "week" : lines[3], "channel" : lines[4], "freq" : lines[5], "coh" : lines[6]}
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
        obs = searchForm.obs.data

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
            return render_template('lineresult.html', dlines=stringListSortedBy, warning="Line search limited to the first 2500 results found. Try confining bounds for a more specific search. Lines with coherences or frequencies outside the ranges shown here may exist.", type=request.form.get('range'))

        if len(dLines) == 0:
            return render_template('lineresult.html', dlines=stringListSortedBy, warning="No lines found. Try loosening bounds for a more broad search.", type=request.form.get('range'))
        
        else:
            return render_template('lineresult.html', dlines=stringListSortedBy, warning="", type=request.form.get('range'))

    if request.method == 'GET':
        return render_template('lineform.html', form=searchForm, errormessage="", helpmessage="")

    else:
        "Something went wrong."

@app.route("/download")
def download():

    csv = str('Type: ,') + str('Run: ' + run + ',') + str('Observatory: ' + obs + ',') + str('Time Range: ' + stTime + ' to ' + enTime + ',') + str('Channel: ' + channel + ',') + str('Frequency: ' + freqLB + ' - ' + freqUB + ',') + str('Coherence: ' + cohLB + ' - ' + cohUB + ',') + '\n'
    for line in dLines:
        csv = csv + str(line) + '\n'
    csv = csv.encode()
    
    return Response(
        csv, 
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=Linefinder.csv"})

if __name__ == '__main__':
    app.run()

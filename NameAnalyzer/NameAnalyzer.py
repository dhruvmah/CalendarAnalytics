# all the imports
from collections import Counter

from flask import Flask, request, session, g, redirect, url_for, abort, \
    render_template, flash, jsonify
import requests
import os
import pytz
import datetime
import dateutil
import sqlite3
from dateutil.parser import parse

import flask
import httplib2

from apiclient import discovery
from oauth2client import client

app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    DATABASE=os.path.join(app.root_path, 'NameAnalyzer.db'),
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('NameAnalyzer_SETTINGS', silent=True)


@app.cli.command('initdb')
def initdb_command():
    """Initializes the database."""
    init_db()
    print('Initialized the database.')


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.route('/entries')
def show_entries():
    db = get_db()
    cur = db.execute('select id, firstname, lastname, gender, probability from entries order by id desc')
    entries = cur.fetchall()
    return render_template('show_entries.html', entries=entries)


@app.route('/')
def index():
    credentials = get_credentials()
    if credentials == None:
        return flask.redirect(flask.url_for('oauth2callback'))

    service = get_calendar(credentials)
    return render_template('show_events.html')


@app.route('/individual/<email>')
def individual(email):
    credentials = get_credentials()
    if credentials == None:
        return flask.redirect(flask.url_for('oauth2callback'))

    service = get_calendar(credentials)
    return render_template('show_individual.html', email=email)



def convert_to_datetimes(events):
    for event in events:
        if "start" in event:
            if "dateTime" in event["start"]:
                start = parse(event["start"]["dateTime"])
                end = parse(event["end"]["dateTime"])
                event["start"]["dateTime"] = start
                event["end"]["dateTime"] = end
                event["duration"] = ((end - start).seconds) / float(3600)
    return events


@app.route('/api/timespent')
def time_spent_api():
    credentials = get_credentials()
    if credentials == None:
        return flask.redirect(flask.url_for('oauth2callback'))

    service = get_calendar(credentials)
    start_date = request.args.get('minDate', "2015-10-30T00:00:00+00:00")
    end_date = request.args.get('maxDate', "2015-11-30T00:00:00+00:00")
    size_filter = request.args.get('sizeFilter', "fiveOrMore")

    end = dateutil.parser.parse(end_date)
    start = dateutil.parser.parse(start_date)
    six_month_start = end - datetime.timedelta(days=6 * 30)

    one_months_events = get_events(service, start, end)
    six_months_events = get_events(service, six_month_start, end)

    (all_people_one_months, names) = get_time_spent_with_others(one_months_events, start, end, size_filter)
    (all_people_six_months, names_six) = get_time_spent_with_others(six_months_events, six_month_start, end,
                                                                    size_filter)
    names.update(names_six)
    response = [
        {
        	"email" : person,
            "displayName": names[person],
            "sixMonthData": time_six_months,
            "oneMonthData": all_people_one_months.get(person, 0)
        } for person, time_six_months in all_people_six_months.items()]

    response = sorted(response, key=lambda a: a["oneMonthData"])
    response = reversed(response)

    person_time = list(response)[0:20]

    return jsonify(person_time)


@app.route('/api/rollups')
def rollups():
    credentials = get_credentials()
    if credentials is None:
        return flask.redirect(flask.url_for('oauth2callback'))

    end_date = request.args.get('maxDate', "2014-10-30T00:00:00+00:00")
    end = dateutil.parser.parse(end_date)
    start = end - datetime.timedelta(days=1 * 30)

    service = get_calendar(credentials)
    one_months_events = get_events(service, start, end)
    valid_meetings = [event for event in one_months_events if is_valid_meeting(event)]

    time_in_meetings = sum([event["duration"] for event in valid_meetings])
    all_attendees = [person for event in valid_meetings for person in get_real_attendees(event)]
    all_unique = set([person["email"] for person in all_attendees])

    (all_people_one_months, names) = get_time_spent_with_others(one_months_events, start, end)
    topFive = sorted(all_people_one_months.items(), key=lambda (email,time): -time)[0:5]
    topFiveNames = [{"name": names[email], "email": email} for (email,time) in topFive]

    response = {
        "timeInMeetings": time_in_meetings,
        "numberOfMeetings": len(valid_meetings),
        "totalPeopleMet": len(all_unique),
        "topFive": topFiveNames
    }

    return jsonify(response)

def person_in_meeting(email, event):
	return email in [attendee["email"] for attendee in event["attendees"]]


@app.route('/api/personStats')
def person_stats():
    credentials = get_credentials()
    if credentials is None:
        return flask.redirect(flask.url_for('oauth2callback'))

    person_email = request.args.get('personEmail', "alex.lee@nutanix.com")
    end_date_param = request.args.get('maxDate', "2014-12-30T00:00:00+00:00")


    end_date = datetime.datetime.combine(dateutil.parser.parse(end_date_param).date().replace(day=1), datetime.datetime.min.time())
    end_date = end_date.replace(tzinfo=pytz.utc)

    start = end_date - dateutil.relativedelta.relativedelta(months=6)

    service = get_calendar(credentials)
    events = get_events(service, start, end_date)
    valid_meetings = [event for event in events if is_valid_meeting(event)]
    person_meetings = [event for event in valid_meetings if person_in_meeting(person_email, event)]

    monthStarts = [start + dateutil.relativedelta.relativedelta(months=i) for i in range(6)]

    meeting_months = {monthStart: [meeting for meeting in person_meetings if event_in_range(meeting, monthStart, monthStart + dateutil.relativedelta.relativedelta(months=1))] for monthStart in monthStarts}

    response = {
        "timeInMeetingsSeries": {monthStart.date().isoformat(): sum([meeting["duration"] for meeting in meetings]) for monthStart, meetings in meeting_months.items()},
        "numberOfMeetingsSeries": {monthStart.date().isoformat(): len(meetings) for monthStart, meetings in meeting_months.items()}
    }

    print response

    return jsonify(response)


def get_events(service, start, end):
    eventsResult = service.events().list(calendarId='primary', timeMin=start.isoformat(), timeMax=end.isoformat(),
                                         maxResults=2500, singleEvents=True, orderBy='startTime').execute()
    events = eventsResult.get('items', [])
    if not events:
        print('No upcoming events found.')
        return []

    return convert_to_datetimes(events)


def get_datetime(year, month):
    time_naive = datetime.datetime(year, month, 1)
    timezone = pytz.timezone("America/Los_Angeles")
    time_aware = timezone.localize(time_naive)
    return time_aware


def event_in_range(event, start, end):
    return event["start"]["dateTime"] >= start and event["end"]["dateTime"] <= end


def localize(raw_datetime):
    timezone = pytz.timezone("America/Los_Angeles")
    return timezone.localize(raw_datetime)


def get_avg_meeting_length(events):
    sum = 0
    count = 0
    for event in events:
        if "duration" in event:
            count += 1
            sum += event["duration"]
    return float(sum) / float(count)


def get_avg_meeting_size(events):
    sum = 0
    count = 0
    for event in events:
        if "attendees" in event:
            sum += len(event["attendees"])
            count += 1
    return float(sum) / float(count)


def get_time_spent_with_others(events, start_time, end_time, size_filter_name="ALL"):
    time_diff = end_time - start_time
    size_filter = get_size_filter(size_filter_name)
    # duration means that we know there's a start and end date
    valid_events = [event for event in events if is_valid_meeting(event)]
    events_within_time = [event for event in valid_events if event["start"]["dateTime"] >= start_time and event["end"]["dateTime"] <= end_time]
    events_within_size = [event for event in events_within_time if size_filter(len(event["attendees"]))]

    names = {attendee["email"]: attendee.get("displayName", attendee["email"]) for event in events_within_size for attendee in get_real_attendees(event)}

    all_people = Counter()
    for event in events_within_size:
        for attendee in get_real_attendees(event):
            all_people[attendee["email"]] += event["duration"]/(time_diff.days / 7)

    return all_people, names


def is_valid_meeting(event):
    return "duration" in event and "attendees" in event and len(get_real_attendees(event)) > 0


def get_real_attendees(event):
    return [attendee for attendee in event["attendees"] if
            attendee["responseStatus"] == "accepted" \
            and (not attendee.has_key('resource') or attendee["resource"] == False) \
            and (not attendee.has_key('self') or attendee["self"] == False)]


def get_size_filter(size_filter):
    if size_filter == 'oneOnOne':
        return lambda size: size == 2
    elif size_filter == 'lessThanFive':
        return lambda size: size < 5
    elif size_filter == 'fiveOrMore':
        return lambda size: size >= 5
    else:
        return lambda size: True


@app.route('/oauth2callback')
def oauth2callback():
    flow = client.flow_from_clientsecrets(
        'client_secrets.json',
        scope='https://www.googleapis.com/auth/calendar.readonly',
        redirect_uri=flask.url_for('oauth2callback', _external=True))
    if 'code' not in flask.request.args:
        auth_uri = flow.step1_get_authorize_url()
        return flask.redirect(auth_uri)
    else:
        auth_code = flask.request.args.get('code')
        credentials = flow.step2_exchange(auth_code)
        flask.session['credentials'] = credentials.to_json()
        return flask.redirect(flask.url_for('index'))


@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    all_full_names = request.form['name'].split("\n")
    print all_full_names
    names_dict = {}
    for name in all_full_names:
        first, last = name.split()
        names_dict[first] = last
    count = 0
    url_params = {}
    for name in names_dict:
        url_params["name[" + str(count) + "]"] = name
        count += 1
    url = 'https://api.genderize.io/'
    print url_params
    r = requests.get(url, url_params)
    db = get_db()
    print r.json()
    print r.headers
    print
    for row in r.json():
        db.execute('insert into entries (firstname, lastname, gender, probability) values (?, ?, ?, ?)',
                   [row["name"], names_dict[row["name"]], row['gender'], row['probability']])
        db.commit()
    flash('New entry was successfully posted')
    return redirect(url_for('show_entries'))


def checkName_Genderize(firstName):
    url = 'https://api.genderize.io/'
    params = {"name": firstName}
    print params
    r = requests.get(url, params=params)
    return (r.json()["gender"], r.json()["probability"])


@app.route('/logindb', methods=['GET', 'POST'])
def logindb():
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            flash('You were logged in')
            return redirect(url_for('show_entries'))
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('You were logged out')
    return redirect(url_for('show_entries'))


def get_credentials():
    if 'credentials' not in flask.session:
        return None
    credentials = client.OAuth2Credentials.from_json(flask.session['credentials'])
    if credentials.access_token_expired:
        return None
    return credentials


def get_calendar(credentials):
    http_auth = credentials.authorize(httplib2.Http())
    return discovery.build('calendar', 'v3', http=http_auth)


def connect_db():
    """Connects to the specific database."""
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv


def init_db():
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()


@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

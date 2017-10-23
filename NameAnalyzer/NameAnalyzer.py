# all the imports
import math
from flask import Flask, redirect, request, session, g, redirect, url_for, abort, \
	 render_template, flash
import requests
import time
import os
import pytz
import datetime
import sqlite3
from dateutil.parser import *

import json

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
	if 'credentials' not in flask.session:
		return flask.redirect(flask.url_for('oauth2callback'))
	credentials = client.OAuth2Credentials.from_json(flask.session['credentials'])
	if credentials.access_token_expired:
		return flask.redirect(flask.url_for('oauth2callback'))
	else:
		http_auth = credentials.authorize(httplib2.Http())
		service = discovery.build('calendar', 'v3', http=http_auth)
		now = datetime.datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
		eventsResult = service.events().list(calendarId='primary', timeMin="2013-01-01T00:00:00-07:00", timeMax= "2016-10-31T00:00:00-07:00", maxResults=2500, singleEvents=True, orderBy='startTime').execute()
		events = eventsResult.get('items', [])
		if not events:
			print('No upcoming events found.')
		for event in events:
			if "start" in event:
				if "dateTime" in event["start"]:
					start = parse(event["start"]["dateTime"])
					end = parse(event["end"]["dateTime"])
					event["start"]["dateTime"] = start
					event["end"]["dateTime"] = end	
					event["duration"] = ((end-start).seconds)/float(3600)
		person_time = time_by_month(events)
		print person_time[0:9]
		return render_template('show_events.html', events=events, values = person_time[1:19])

def get_datetime(year, month):
	time_naive = datetime.datetime(year, month, 1)
	timezone = pytz.timezone("America/Los_Angeles")
	time_aware = timezone.localize(time_naive)
	return time_aware

def time_by_month(events):
	# today = datetime.datetime(2015, 11, 1)
	(all_people_six_months, names) = get_time_spent_with_others(events, get_datetime(2015, 1), get_datetime(2015, 6))
	all_people_six_months = {person: time/6 for person,time in all_people_six_months.items()}
	(all_people_one_months, ignore) = get_time_spent_with_others(events, get_datetime(2015, 5), get_datetime(2015, 6))
	response = [
		{
			"displayName": names[person],
			"sixMonthData": time_six_months,
			"oneMonthData": all_people_one_months.get(person, 0)
		} for person, time_six_months in all_people_six_months.items()]

	response = sorted(response, key=lambda a:a["oneMonthData"])
	response = reversed(response)

	return list(response)


def get_avg_meeting_length(events):
	sum = 0
	count = 0
	for event in events:
		if "duration" in event:
			count+=1
			sum+= event["duration"]
	return float(sum)/float(count)

def get_avg_meeting_size(events):
	sum = 0
	count = 0
	for event in events:
		if "attendees" in event:
			sum += len(event["attendees"])
			count+=1
	return float(sum)/float(count)

def get_time_spent_with_others(events, start_time, end_time):
	all_people = {}
	names = {}
	for event in events:
		#duration means that we know there's a start and end date
		if "duration" in event and "attendees" in event:
			if event["start"]["dateTime"] >= start_time and event["end"]["dateTime"] <= end_time:
				for attendee in event["attendees"]:
					if attendee["responseStatus"] == "accepted":
						all_people[attendee["email"]] = 0
						names[attendee["email"]] = attendee.get("displayName", attendee["email"])
						
	for event in events:
		#duration means that we know there's a start and end date
		if "duration" in event and "attendees" in event:
			if event["start"]["dateTime"] >= start_time and event["end"]["dateTime"] <= end_time:		
				for attendee in event["attendees"]:
					if attendee["email"] in all_people:
						all_people[attendee["email"]] += event["duration"]
	return (all_people, names)


#	print all_people
#						all_people[attendee["email"]][(event["start"]["dateTime"].month, event["start"]["dateTime"].year)] += event["duration"]
#					else:
#						all_people[attendee["email"]] = {}
#						if (event["start"]["dateTime"].month, event["start"]["dateTime"].year) in all_people[attendee["email"]]:
#							all_people[attendee["email"]][(event["start"]["dateTime"].month, event["start"]["dateTime"].year)] += event["duration"]
#						else:
#							all_people[attendee["email"]][(event["start"]["dateTime"].month, event["start"]["dateTime"].year)] = event["duration"]

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
	names_dict={}
	for name in all_full_names:
		first,last = name.split()
		names_dict[first] = last
	count = 0
	url_params = {}
	for name in names_dict:
		url_params["name[" + str(count) + "]"] = name
		count +=1
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

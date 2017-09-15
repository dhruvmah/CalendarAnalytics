# all the imports
import os
import sqlite3
from flask import Flask, request, session, g, redirect, url_for, abort, \
     render_template, flash
import requests
import time


app = Flask(__name__) # create the application instance :)
app.config.from_object(__name__) # load config from this file , NameAnalyzer.py



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


@app.route('/')
def show_entries():
    db = get_db()
    cur = db.execute('select id, firstname, lastname, gender, probability from entries order by id asc')
    entries = cur.fetchall()
    return render_template('show_entries.html', entries=entries)

@app.route('/add', methods=['POST'])
def add_entry():
    if not session.get('logged_in'):
        abort(401)
    all_full_names = request.form['name'].split("\n")
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
    r = requests.get(url, url_params)
    db = get_db()
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


@app.route('/login', methods=['GET', 'POST'])
def login():
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

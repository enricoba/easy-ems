# -*- coding: utf-8 -*-
"""
Initiation module for eems.
"""

# import external modules
import os
import collections
from threading import Thread, Lock
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy


# import eems modules
from sensors import ds18b20


class _SensorDictionary(object):
    def __init__(self, s_list):
        tmp = dict()
        for s in sorted(s_list):
            tmp[s] = None
        self.dic = collections.OrderedDict(sorted(tmp.items(), key=lambda t: t[0]))
        self.lock = Lock()

    def set_temp(self, sensor, temp):
        with self.lock:
            self.dic.__setitem__(sensor, temp)

    def get_dic(self):
        return self.dic

    def reset_dic(self):
        for sensor in self.dic.keys():
            self.dic.__setitem__(sensor, None)


"""
eems project information
"""


__project__ = 'eems'
__version__ = '0.2.0.1b1'
__copyright__ = '2015-2016, Henrik Baran, Aurofree Hoehn'
__author__ = 'Henrik Baran, Aurofree Hoehn'


# Flask object
app = Flask(__name__)
# check if server or development environment
if os.path.exists('/var/www/eems/eems/data/'):
    path = '/var/www/eems/eems/data/config.db'
else:
    print os.path.dirname(__file__)
    path = '{}/data/config.db'.format(os.path.dirname(__file__))
    print path
    # path = '/home/pi/git_hub/eems/eems/data/config.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////{}'.format(path)

db = SQLAlchemy(app)


class General(db.Model):
    __tablename__ = 'general'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    item = db.Column(db.Text)
    value = db.Column(db.Text)

    def __init__(self, item=None, value=None):
        self.item = item
        self.value = value


class Content(db.Model):
    __tablename__ = 'content'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    position = db.Column(db.Text)
    german = db.Column(db.Text)
    english = db.Column(db.Text)

    def __init__(self, position=None, german=None, english=None):
        self.position = position
        self.german = german
        self.english = english


class Sessions(db.Model):
    __tablename__ = 'sessions'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    session = db.Column(db.Text)

    def __init__(self, session=None):
        self.session = session


class SensorsUsed(db.Model):
    __tablename__ = 'sensors_used'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    code = db.Column(db.Text)
    name = db.Column(db.Text)
    value = db.Column(db.REAL)
    session_id = db.Column(db.Integer)
    sensor_id = db.Column(db.Integer)

    def __init__(self, code=None, name=None, value=None, session_id=None, sensor_id=None):
        self.code = code
        self.name = name
        self.value = value
        self.session_id = session_id
        self.sensor_id = sensor_id


class SensorsSupported(db.Model):
    __tablename__ = 'sensors_supported'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.Text)
    typ = db.Column(db.Text)
    unit = db.Column(db.Text)

    def __init__(self, name=None, typ=None, unit=None):
        self.name = name
        self.typ = typ
        self.unit = unit


class Data(db.Model):
    __tablename__ = 'data'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    timestamp = db.Column(db.Integer)
    value = db.Column(db.Float)
    session_id = db.Column(db.Integer)
    sensor_name_id = db.Column(db.Integer)

    def __init__(self, timestamp=None, value=None, session_id=None, sensor_name_id=None):
        self.timestamp = timestamp
        self.value = value
        self.session_id = session_id
        self.sensor_name_id = sensor_name_id


# db.create_all()
# db.session.commit()


def __db_content(lang):
    tmp_dict = dict()
    content = Content.query.all()
    for i in content:
        if lang == 'de':
            tmp_dict[i.position] = i.german
        elif lang == 'en':
            tmp_dict[i.position] = i.english
    return tmp_dict


def __db_general():
    tmp_dict = dict()
    general = General.query.all()
    for i in general:
        tmp_dict[i.item] = i.value
    return tmp_dict


@app.route('/', methods=['GET', 'POST'])
def start():
    return redirect(url_for('index', lang='en'))


@app.route('/<string:lang>/', methods=['GET', 'POST'])
def index(lang=None):
    # level-0 :: CONTENT
    if lang is None:
        content = __db_content('en')
    else:
        language = General.query.filter_by(item='LANGUAGE').first()
        language.value = lang
        db.session.commit()
        content = __db_content(lang)

    profiles = [content['HOME_NEW'].encode('utf-8')]
    sessions = Sessions.query.all()
    for i in sessions:
        profiles.append(i.session.encode('utf-8'))

    if request.method == 'POST':
        if 'session-start' in request.form:
            # get new session input
            profile_tmp = request.form['session-input']

            # verify if new session (input text has a length) or existing session (length = 0)
            if len(profile_tmp):
                session = General.query.filter_by(item='SESSION').first()
                session.value = profile_tmp
                session_add = Sessions(profile_tmp)
                db.session.add(session_add)
            else:
                profile_load = request.form['session-load']
                session = General.query.filter_by(item='SESSION').first()
                session.value = profile_load

            # update session related information
            status = General.query.filter_by(item='NAVBAR_STATUS').first()
            icon = General.query.filter_by(item='SESSION_ICON').first()
            color = General.query.filter_by(item='SESSION_COLOR').first()
            status.value = ''
            icon.value = 'lock'
            color.value = 'green'
            db.session.commit()

            # get session id from sessions table by session name of general table
            query = General.query.filter_by(item='SESSION').first()
            s_id = Sessions.query.filter_by(session=query.value).first()

            # update session_id in general table
            session_id = General.query.filter_by(item='SESSION_ID').first()
            session_id.value = s_id.id
            db.session.commit()

            return redirect(url_for('config', lang=lang))
        elif 'sessionLogout' in request.form:
            session = General.query.filter_by(item='SESSION').first()
            status = General.query.filter_by(item='NAVBAR_STATUS').first()
            icon = General.query.filter_by(item='SESSION_ICON').first()
            color = General.query.filter_by(item='SESSION_COLOR').first()
            session_id = General.query.filter_by(item='SESSION_ID').first()
            session.value = '-'
            status.value = 'disabled'
            icon.value = 'unlock'
            color.value = 'darkred'
            session_id.value = '-'
            db.session.commit()

            # level-99 :: CONFIG
            global_data = __db_general()
            return render_template('index.html', name='index',
                                   global_data=global_data,
                                   content=content,
                                   profiles=profiles, len=len(profiles))
    else:
        # level-99 :: CONFIG
        global_data = __db_general()
        return render_template('index.html', name='index',
                               global_data=global_data,
                               content=content,
                               profiles=profiles, len=len(profiles))


@app.route('/config/', methods=['GET', 'POST'])
@app.route('/<string:lang>/config/', methods=['GET', 'POST'])
def config(lang=None):
    # level-0 :: CONTENT
    if lang is None:
        content = __db_content('en')
    else:
        language = General.query.filter_by(item='LANGUAGE').first()
        language.value = lang
        db.session.commit()
        content = __db_content(lang)

    # level-2 :: HANDLING
    if request.method == 'POST':
        # level-99 :: CONFIG
        global_data = __db_general()
        return render_template('index.html', name='config',
                               global_data=global_data,
                               content=content)
    else:
        query = General.query.filter_by(item='SESSION').first()
        tmp = Sessions.query.filter_by(session=query.value).first()
        session_id = tmp.id

        query = General.query.filter_by(item='SESSION_ID').first()
        print query.value, type(query.value)

        # level-10 :: SENSORS - DS18B20
        query = SensorsSupported.query.filter_by(name='ds18b20').first()
        sensor_id = query.id
        s_ds18b20 = ds18b20.DS18B20()
        s_list = s_ds18b20.detect()
        if len(s_list):
            # function to get sensor values
            s_dict = _SensorDictionary(s_list)
            threads = list()
            for s in s_list:
                threads.append(Thread(target=s_ds18b20.read, args=(s, s_dict)))
            for t in threads:
                t.setDaemon(True)
                t.start()
            for t in threads:
                t.join()
            for code in s_list:
                sensor = SensorsUsed.query.filter_by(code=code, session_id=session_id).first()
                if sensor is None:
                    tmp = SensorsUsed(code=code, value=s_dict.dic[code], session_id=session_id, sensor_id=sensor_id)
                    db.session.add(tmp)
                else:
                    sensor.value = s_dict.dic[code]
            db.session.commit()

        # level-99 :: DB
        sensors_used = SensorsUsed.query.all()
        sensors_supported = SensorsSupported.query.all()

        global_data = __db_general()
        return render_template('index.html', name='config',
                               global_data=global_data,
                               content=content,
                               sensors_used=sensors_used,
                               sensors_supported=sensors_supported)


@app.route('/monitor/')
@app.route('/<string:lang>/monitor/')
def monitor(lang=None):
    # level-0 :: CONTENT
    if lang is None:
        content = __db_content('en')
    else:
        language = General.query.filter_by(item='LANGUAGE').first()
        language.value = lang
        db.session.commit()
        content = __db_content(lang)

    # level-99 :: CONFIG
    global_data = __db_general()
    return render_template('index.html', name='monitor',
                           global_data=global_data,
                           content=content)


@app.route('/licence/')
@app.route('/<string:lang>/licence/')
def licence(lang=None):
    # level-0 :: CONTENT
    if lang is None:
        content = __db_content('en')
    else:
        language = General.query.filter_by(item='LANGUAGE').first()
        language.value = lang
        db.session.commit()
        content = __db_content(lang)

    # level-99 :: CONFIG
    global_data = __db_general()
    return render_template('index.html', name='licence',
                           global_data=global_data,
                           content=content)


if __name__ == "__main__":
    # in deployment MUST be False !!!
    app.debug = True
    app.run(host='0.0.0.0')

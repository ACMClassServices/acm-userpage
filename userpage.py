#!/usr/bin/env python3

import functools
import os
import re
import sqlite3
from base64 import b32encode
from http.client import FORBIDDEN, INTERNAL_SERVER_ERROR, UNAUTHORIZED

import requests
from flask import (Flask, abort, flash, g, make_response, redirect,
                   render_template, request, session, url_for)
from requests_oauthlib import OAuth2Session

from config import *
from migrate import is_up_to_date

app = Flask(__name__, static_url_path=WEBROOT + '/static')
app.secret_key = FLASK_SECRET_KEY


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        conn = sqlite3.connect(DB_NAME)
        if not is_up_to_date(conn):
            abort(INTERNAL_SERVER_ERROR, 'Database migration needed')
        conn.row_factory = sqlite3.Row
        db = g._database = conn
    return db


def generate_token():
    return b32encode(os.urandom(10)).decode().lower()


def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('请登入', 'error')
            return redirect(url_for('homepage'))
        return f(*args, **kwargs)
    return decorated_function


def logout_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' in session:
            flash('请登出', 'error')
            return redirect(url_for('homepage'))
        return f(*args, **kwargs)
    return decorated_function


@app.get(WEBROOT)
def homepage():
    user = session.get('user', None)

    cur = get_db().cursor()
    sql = '''SELECT sites.slug AS slug, members.stuid AS stuid, members.name AS name
    FROM sites, members
    WHERE sites.stuid = members.stuid
    ORDER BY members.stuid DESC'''
    cur.execute(sql)
    known_users = cur.fetchall()
    stuid = user['stuid'] if user is not None else None
    user_slug = [x['slug'] for x in known_users if x['stuid'] == stuid]
    user_slug = None if len(user_slug) == 0 else user_slug[0]

    return render_template('homepage.html', user=user, user_slug=user_slug, known_users=known_users)


@app.get(WEBROOT + '/help')
def help():
    return render_template('help.html')


@app.get(WEBROOT + '/token')
@login_required
def set_token():
    return render_template('token.html')

@app.post(WEBROOT + '/token')
@login_required
def do_set_token():
    jaccount = session['user']['jaccount']
    stuid = session['user']['stuid']

    token = generate_token()
    cur = get_db().cursor()
    cur.execute('INSERT OR IGNORE INTO sites (jaccount, stuid, slug, token) VALUES (?, ?, ?, ?)', (jaccount, stuid, jaccount, token))
    cur.execute('UPDATE sites SET token = ? WHERE jaccount = ? AND stuid = ?', (token, jaccount, stuid))
    slug = cur.execute('SELECT slug FROM sites WHERE jaccount = ?', (jaccount, )).fetchone()[0]
    get_db().commit()

    resp = requests.post(GITD_API_URL + '/repo', data={ 'path': 'userpage/' + slug, 'max_size_bytes': 100 * 1048576, 'serve': 'true' })
    if resp.status_code > 299:
        print('Error creating git repo: ' + resp.text)
        flash(f'创建 Git repo 失败 ({resp.status_code})', 'error')

    return render_template('token_result.html', jaccount=jaccount, slug=slug, token=token)

@app.get(WEBROOT + '/repo/reset')
@login_required
def reset_repo():
    return render_template('reset_repo.html')

@app.post(WEBROOT + '/repo/reset')
@login_required
def do_reset_repo():
    if request.form['confirm'] != '确认删除':
        flash('请确认删除操作', 'error')
        return redirect(url_for('reset_repo'))

    jaccount = session['user']['jaccount']
    slug = get_db().execute('SELECT slug FROM sites WHERE jaccount = ?', (jaccount, )).fetchone()[0]

    resp = requests.delete(GITD_API_URL + '/repo', data={ 'path': 'userpage/' + slug })
    if resp.status_code > 299:
        print('Error deleting git repo: ' + resp.text)
        flash(f'删除 Git repo 失败 ({resp.status_code})', 'error')
        return redirect(url_for('reset_repo'))
    resp = requests.post(GITD_API_URL + '/repo', data={ 'path': 'userpage/' + slug, 'max_size_bytes': 100 * 1048576, 'serve': 'true' })
    if resp.status_code > 299:
        print('Error creating git repo: ' + resp.text)
        flash(f'创建 Git repo 失败 ({resp.status_code})', 'error')
        return redirect(url_for('reset_repo'))

    flash('已重建 Git 仓库')
    return redirect(url_for('homepage'))


@app.get(WEBROOT + '/login')
@logout_required
def login():
    redirect_uri = DOMAIN + url_for('login_oauth_callback')
    sjtu = OAuth2Session(CLIENT_ID, redirect_uri=redirect_uri, scope='basic essential profile')
    authorization_url, state = sjtu.authorization_url(AUTHORIZATION_BASE_URL)
    session['oauth_state'] = state
    return redirect(authorization_url)


@app.get(WEBROOT + '/login/oauth/callback')
@logout_required
def login_oauth_callback():
    code = request.args.get('code', None)
    state = session.get('oauth_state', None)
    if not code:
        flash('login_oauth_callback: no code', 'error')
        return redirect(url_for('homepage'))
    if not state:
        flash('login_oauth_callback: no oauth_state', 'error')
        return redirect(url_for('homepage'))

    redirect_uri = DOMAIN + url_for('login_oauth_callback')
    sjtu = OAuth2Session(CLIENT_ID, state=state, redirect_uri=redirect_uri)
    token = sjtu.fetch_token(TOKEN_URL, client_secret=CLIENT_SECRET, code=code)
    session['oauth_token'] = token

    res = sjtu.get(PROFILE_URL).json()
    res = res['entities'][0]

    cur = get_db().cursor()
    cur.execute('SELECT * FROM members WHERE stuid=?', (res['code'], ))
    row = cur.fetchone()
    if not row:
        flash('您不是 ACM 班的成员', 'error')
        return redirect(url_for('homepage'))

    user = {
        'jaccount': res['account'],
        'name': res['name'],
        'stuid': res['code'],
    }

    session['user'] = user
    return redirect(url_for('homepage'))


@app.post(WEBROOT + '/logout')
@login_required
def logout():
    session.clear()
    flash('已登出', 'success')
    url = f'{LOGOUT_URL}?client_id={CLIENT_ID}&redirect_uri={DOMAIN}{url_for("homepage")}'
    return redirect(url)


@app.route('/auth')
def auth():
    uri = request.headers['x-original-uri']
    uri_regex = re.compile(r'^/~([^/]+)/\.git/(.*)$')
    match = uri_regex.match(uri)
    if not match:
        abort(FORBIDDEN)
    slug = match[1]

    user = session.get('user', None)
    if user:
        cur = get_db().cursor()
        cur.execute('SELECT * FROM sites WHERE jaccount = ? AND slug = ?', (user['jaccount'], slug))
        row = cur.fetchone()
        if not row:
            abort(FORBIDDEN)
        return 'Authorised'

    auth = request.authorization
    if auth is None or auth.type != 'basic':
        resp = make_response()
        resp.status_code = UNAUTHORIZED
        resp.headers.set('WWW-Authenticate', 'Basic realm="ACM Userpage Git Access", charset="UTF-8"')
        abort(resp)

    jaccount = auth.username
    token = auth.password

    cur = get_db().cursor()
    cur.execute('SELECT * FROM sites WHERE jaccount = ? AND token = ? AND slug = ?', (jaccount, token, slug))
    row = cur.fetchone()
    if not row:
        abort(UNAUTHORIZED)

    return 'Authorised'


if __name__ == '__main__':
    app.run('0.0.0.0', port=5869, debug=True)

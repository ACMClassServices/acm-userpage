import sqlite3

import requests

from config import DB_NAME, GITD_API_URL
from migrate import is_up_to_date

db = sqlite3.connect(DB_NAME)
if not is_up_to_date(db):
    print('Database migration required')
    exit(1)

slugs = [x[0] for x in db.execute('select slug from sites;').fetchall()]
for slug in slugs:
    resp = requests.post(GITD_API_URL + '/repo', data={ 'path': 'userpage/' + slug, 'max_size_bytes': 100 * 1048576, 'serve': 'true' })
    if resp.status_code > 299:
        print(f'Error creating git repo for {slug}: {resp.text}')

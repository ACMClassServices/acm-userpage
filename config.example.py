import os

DOMAIN = 'http://localhost:5869'
# DOMAIN = 'https://acm.sjtu.edu.cn'
WEBROOT = '/userpage-manage'
FLASK_SECRET_KEY = 'you can copy from: python -c "print(repr(__import__(\"os\").urandom(30)))"'
DB_NAME = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'userpage.db')
# DB_NAME = '/srv/userpage/userpage.db'

CLIENT_ID = 'your oauth2 client id'
CLIENT_SECRET = 'your oauth2 client secret'
AUTHORIZATION_BASE_URL = 'https://jaccount.sjtu.edu.cn/oauth2/authorize'
TOKEN_URL = 'https://jaccount.sjtu.edu.cn/oauth2/token'
LOGOUT_URL = 'https://jaccount.sjtu.edu.cn/oauth2/logout'
PROFILE_URL = 'https://api.sjtu.edu.cn/v1/me/profile'

GITD_API_URL = 'http://user:pass@localhost:82'
# GITD_API_URL = 'http://user:pass@host-gateway.internal:82'

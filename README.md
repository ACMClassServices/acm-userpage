# acm-userpage

Host academic homepage for ACM Class students with URL like `https://acm.sjtu.edu.cn/~jaccount`. Go to management here: <https://acm.sjtu.edu.cn/userpage-manage>.

## Server Setup

```
$ sudo apt-get install nginx
$ sudo vim /etc/nginx/sites-enabled/default
location = /userpage-auth {
    internal;
    proxy_pass http://gunicorn;
    proxy_pass_request_body off;
    proxy_set_header Content-Length "";
    proxy_set_header X-Original-URI $request_uri;
}
location ~ ^/~([0-9a-zA-Z_-]+)\.git/(HEAD|info/refs|objects/(info/[^/]+|[0-9a-f]+/[0-9a-f]+|pack/pack-[0-9a-f]+\.(pack|idx))|git-(upload|receive)-pack)$ {
    auth_request /userpage-auth;
    proxy_pass http://gitd:80/userpage/$1/$2$is_args$args;
    proxy_redirect http://gitd:80/userpage/$1 /~$1.git;
    proxy_set_header Authorization "Basic GITDAUTHBASE64";
}
location ~ ^/~([0-9a-zA-Z_-]+)\.git/(.*)$ {
    auth_request /userpage-auth;
    proxy_pass http://gitd:80/userpage/$1/$2$is_args$args;
    proxy_redirect http://gitd:80/userpage/$1 /~$1.git;
    proxy_set_header Authorization "Basic GITDAUTHBASE64";
    sub_filter "/GITD_CGIT_VIRTUAL_ROOT_zT0Ohfr3SNbdeP4c/userpage/$1/" "/~$1.git/";
    sub_filter_last_modified on;
    sub_filter_once off;
}
location ~ ^/~(.+)$ {
    proxy_pass http://gitd:81/userpage/$1$is_args$args;
    proxy_redirect http://gitd:81/userpage/$1 /~$1;
    proxy_set_header Authorization "Basic GITDAUTHBASE64";
}
location /_cgit/ {
    proxy_pass http://gitd:80/_cgit/;
    proxy_set_header Authorization "Basic GITDAUTHBASE64";
}
location ~ ^/userpage-manage(/.*)?$ {
    proxy_pass http://gunicorn;
}
$ sudo service nginx reload

# debug run
$ python3 userpage.py
```

## Reference

* OAuth2
    * <http://developer.sjtu.edu.cn/wiki/JAccount>
    * <https://aaronparecki.com/oauth-2-simplified/>

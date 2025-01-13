FROM alpine:3.21.2

RUN apk add --no-cache python3 py3-pip bash sqlite

COPY requirements.txt /opt/userpage/requirements.txt 
RUN pip3 install --break-system-packages -r /opt/userpage/requirements.txt

RUN addgroup -S userpage && adduser -S userpage -G userpage
RUN mkdir -p /srv/userpage && chown userpage:userpage /srv/userpage

COPY . /opt/userpage

USER userpage:userpage
WORKDIR /opt/userpage
RUN python3 migrate.py

VOLUME /srv/userpage

CMD ["/usr/bin/gunicorn", "-w", "4", "--access-logfile", "/srv/userpage/access.log", "--log-file", "/srv/userpage/gunicorn.log", "-b", "0.0.0.0:83", "userpage:app"]

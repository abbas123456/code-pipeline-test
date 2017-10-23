FROM python:2

WORKDIR /usr/src/app

ADD bar bar
ADD foo foo

EXPOSE 8000

CMD [ "python", "-m",  "SimpleHTTPServer", "8000" ]

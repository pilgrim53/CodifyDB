FROM ubuntu:latest
RUN apt-get -y update
RUN apt-get install python3 -y

WORKDIR /python
COPY requirements.txt /python/
RUN apt-get install python3-pip -y
RUN pip install --upgrade pip
# install psycopg2 dependencies
RUN apt-get -y update
RUN apt-get install postgresql-server-dev-all gcc python3-dev musl-dev -y
RUN pip install -r requirements.txt

ENTRYPOINT /bin/bash

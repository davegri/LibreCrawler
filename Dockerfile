FROM python:latest
WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app/
RUN pip install -r requirements.txt
COPY . /usr/src/app
CMD [ "python", "crawl.py" ]

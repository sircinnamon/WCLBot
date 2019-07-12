FROM python:3.7.4-alpine
RUN pip install discord requests
RUN apk add git
RUN pip install git+https://github.com/sircinnamon/pycraftlogs.git
ADD WCLBot.py /WCL/WCLBot.py
ADD ServerInfo.py /WCL/ServerInfo.py
WORKDIR /WCL/
CMD python -u /WCL/WCLBot.py

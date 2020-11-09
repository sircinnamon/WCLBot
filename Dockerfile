FROM python:3.8.6-alpine
RUN MULTIDICT_NO_EXTENSIONS=1 YARL_NO_EXTENSIONS=1 pip install discord requests
RUN apk add git
RUN pip install git+https://github.com/sircinnamon/pycraftlogs.git
ADD WCLBot.py /WCL/WCLBot.py
ADD ServerInfo.py /WCL/ServerInfo.py
WORKDIR /WCL/
CMD python -u /WCL/WCLBot.py

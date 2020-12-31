FROM python:3.8.6-alpine
RUN apk add --no-cache gcc libc-dev git
RUN MULTIDICT_NO_EXTENSIONS=1 YARL_NO_EXTENSIONS=1 pip install discord requests requests_oauthlib python-dateutil
ADD WCLBot.py /WCL/WCLBot.py
ADD ServerInfo.py /WCL/ServerInfo.py
ADD ApiConnector.py /WCL/ApiConnector.py
ADD cogs /WCL/cogs
WORKDIR /WCL/
CMD python -u /WCL/WCLBot.py

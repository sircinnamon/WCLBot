#!/bin/bash

if [ ! -d "logs" ]; then
	mkdir "logs"
fi

if [ ! -d "serverdata" ]; then
	mkdir "serverdata"
fi

if [ ! -e ".keyfile" ]; then
	echo "Keyfile missing: '.keyfile'"
	exit 1
fi

docker stop wcl
docker rm wcl
docker run \
	-d \
	--name wcl \
	-v $(pwd)/serverdata:/WCL/data \
	-v $(pwd)/logs:/WCL/logs \
	-v $(pwd)/.keyfile:/WCL/.keyfile \
	-v /etc/localtime:/etc/localtime:ro \
	wclbot:latest

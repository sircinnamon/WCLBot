#!/bin/bash

if [ -d "logs" ]; then
	mkdir "logs"
fi

if [ -d "serverdata" ]; then
	mkdir "serverdata"
fi

if [ ! -e ".keyfile" ]; then
	echo "Keyfile missing: '.keyfile'"
fi

docker stop wcl
docker rm wcl
docker run \
	-d --rm \
	--name wcl \
	-v $(pwd)/serverdata:/WCL/serverdata \
	-v $(pwd)/logs:/WCL/logs \
	-v $(pwd)/.keyfile:/WCL/.keyfile \
	wclbot:latest

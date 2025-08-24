#!/usr/bin/make
build:
	docker build -t peppy:latest .

lint:
	pre-commit run --all-files

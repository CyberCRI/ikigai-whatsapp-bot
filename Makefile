ifneq ("$(wildcard .env)","")
include .env
endif

# RUN STYLE CHECKS
.PHONY: style
style:
	poetry run black ikigai_whatsapp_bot/
	poetry run isort ikigai_whatsapp_bot/
	poetry run pylint ikigai_whatsapp_bot/

# START MYKOLA's LOCAL SERVER FROM YOUR COMPUTER
.PHONY: start
start:
	python ./ikigai_whatsapp_bot/main.py

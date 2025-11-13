#!/bin/bash
cd ~/Downloads/oracle_rasp_pi_codex2/raspberry_pi || exit
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000

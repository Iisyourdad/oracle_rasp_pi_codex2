#!/bin/bash
cd ~/Downloads/final_rasp_pi_recipe || exit
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000

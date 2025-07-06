#!/usr/bin/env bash
# Force Python 3.11
pyenv install 3.11.8 -s
pyenv global 3.11.8
pip install --upgrade pip
pip install -r requirements.txt

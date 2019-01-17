# py-sure-petcare

[![License: GPL](https://img.shields.io/badge/License-GPL-yellow.svg)](https://opensource.org/licenses/GPL)
[![PyPI version](https://badge.fury.io/py/py-sure-petcare.svg)](https://badge.fury.io/py/py-sure-petcare)
[![Build Status](https://travis-ci.org/grm/py-sure-petcare.svg?branch=master)](https://travis-ci.org/grm/py-sure-petcare)
[![Python 3](https://pyup.io/repos/github/grm/py-sure-petcare/python-3-shield.svg)](https://pyup.io/repos/github/grm/py-sure-petcare/)
[![Maintainability](https://api.codeclimate.com/v1/badges/d797e1085dab74db558c/maintainability)](https://codeclimate.com/github/grm/py-sure-petcare/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/d797e1085dab74db558c/test_coverage)](https://codeclimate.com/github/grm/py-sure-petcare/test_coverage)
[![codecov](https://codecov.io/gh/grm/py-sure-petcare/branch/master/graph/badge.svg)](https://codecov.io/gh/grm/py-sure-petcare)
[![Updates](https://pyup.io/repos/github/grm/py-sure-petcare/shield.svg)](https://pyup.io/repos/github/grm/py-sure-petcare/)
[![Known Vulnerabilities](https://snyk.io/test/github/grm/py-sure-petcare/badge.svg?targetFile=requirements.txt)](https://snyk.io/test/github/grm/py-sure-petcare?targetFile=requirements.txt)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![PEP8](https://img.shields.io/badge/code%20style-pep8-orange.svg)](https://www.python.org/dev/peps/pep-0008/)
[![Downloads](https://pepy.tech/badge/py-sure-petcare)](https://pepy.tech/project/py-sure-petcare)

## Description

Python library for accessing sure connect petflap

Flap Status:
0 : Unlocked
1 : Keep pets in 
2 : Keep pets out
3 : Locked both ways
4 : Curfew mode

Data types:
 0 : Registered animal entered/left
 6 : Lock status changed, locked in/out or curfew change
 7 : Unregistered animal entered/left
12 : User/new user info
20 : Curfew information, Not available as "viewer" user

Movement types:
 0 : Manual entry/leaving registration
 4 : Animal looked through the door
 6 : Standard entry/leaving
 8 : Standard entry
11 : Animal left house
13 : Animal left house


Issues : 
Device id generation is currently taken from the mac address, we should proably find out how sure do it in their app.
Currently we update everything, possibly no point if we are only interested in one animal.
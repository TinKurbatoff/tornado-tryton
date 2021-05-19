# Project Name
> Adds Tryton support to Tornado application.
> Live demo — TO DO [_here_](https://api.example.com). <!-- If you have the project hosted somewhere, include the link here. -->

> Please, add stars to this project if this was helpful for your project. Share your questions and thoughts. Always welcome! 

## Table of Contents
* [General Info](#general-information)
* [Technologies Used](#technologies-used)
* [Features](#features)
* [Screenshots](#screenshots)
* [Setup](#setup)
* [Usage](#usage)
* [Project Status](#project-status)
* [Room for Improvement](#room-for-improvement)
* [Acknowledgements](#acknowledgements)
* [Contact](#contact)
<!-- * [License](#license) -->


## General Information
- This module helps connecting to tryton back-end from Tornado web application 
- I created a Mobile App that used datat from Tryton DB to operate, there is a flask_tryton module exists, but I don't want to use flask as it blocking server and doesn't intendend to use in multy-user multi-tasking operations. As I use Tornado as API back-end I needed to connect tornado back-end to Tryton DB and it's models. 
- I created this module to 
- Why did you undertake it?
<!-- You don't have to answer all the questions - just the ones relevant to your project. -->


## Technologies Used
- trytond - version 5.8.1
- tornado - version 6.1


## Features
List the ready features here:
- Supports async operations (the main advantage of using Tornado over Flask)
- Reads/writes to Tryton database in non-blocking manner.
- Supports all data models, including user-defined, from the Pool of the installed Tryton ERP.



## Screenshots
![Example screenshot](./img/screenshot.png)
<!-- If you have screenshots you'd like to share, include them here. -->


## Setup
What are the project requirements/dependencies? Where are they listed? A requirements.txt or a Pipfile.lock file perhaps? Where is it located?

Proceed to describe how to install / setup one's local environment / get started with the project.


## Usage
By default transactions are readonly except for PUT, POST, DELETE and PATCH request methods. 
You need trytond with all your user modules installed and proper trytond.conf database configuration set:
```
[database]
uri =  postgresql://tryton:<my_secret_password>@postgres:5432/
```

```
#!python3
from tornado_tryton import Tryton # class to connect to Tryton DB

import json

## Tornado webserver modules
from tornado.web import RequestHandler
from tornado.gen import coroutine # used for async execution in earlier version of Python 
from tornado.options import define, options # to access to a server-wide configuration 

TRYTON_CONFIG = '/etc/trytond.conf' # Check Tryton's doc for Tryton configuration details, access to Tryton DB is configured here 

############## TRYTON INTEGRATION #################
define('config', default={"TRYTON_DATABASE" : "tryton", "TRYTON_CONFIG" : TRYTON_CONFIG}, help='app config path')
tryton = Tryton(options)
User = tryton.pool.get('res.user') # Important class type - User

@tryton.default_context # To create a default context of Tryton transactions
def default_context():
    return User.get_preferences(context_only=True)
## —————————————————————————————————————————————————————————

###########  RESPONDER FOR API REQUEST, HTML requests are handled in the same way.
class TrytonUser(RequestHandler):
    """Request for log in to Tryton"""
    SUPPORTED_METHODS = ("GET", "POST",)

    def jsonify(self, data, status=200):
        header = "Content-Type"
        body = "application/json"
        self.set_header(header, body)
        self.set_status(status)
        self.write(json.dumps(data))

    @tryton.transaction() ## To initiate tryton transaction and pass "local" request details 
    async def post(self, login, password):            

        # Check login and authorize
        user = User.search([('login', 'ilike', login)]) # Use `ilike` to ignore char case in login             
        if len(user)>0:
            # So, login is exist
            user, = User.search([('login', 'ilike', login)]) # to get the the first from the list if many
            parameters = {}
            parameters['password'] = password
            user_id = User.get_login(user.login, parameters) # bicrypt hash function
            if user_id:
                ## If user_id found — everyting is correct
                return self.jsonify(data={"result" : "success"}, status = 200)
            else:
                ## If none found — password is incorrect
                return self.jsonify({"result" : "wrong password"}, status=401)
        else:
            return self.jsonify({"result" : "unknown user"}, status=401)
```


## Project Status
Project is: _in progress_ .


## Room for Improvement
It is tested with the only one server configuration and may have some issues in production.

Room for improvement:
- Test with more than 10 concurrent connections
- Add a large file-handling support

To do:
- TODO: Switch context if there are MANY Tryton databases/accounts available.
- TODO: e-mailing support


## Acknowledgements
Give credit here.
- This project was inspired by [Tryton community](https://discuss.tryton.org/)...
- This project is based on the flask_tryton module at [PyPi](https://pypi.org/project/flask-tryton/)...
- Many thanks to Cédric Krier for support of the Tryton project and promt ansewers on the forum.


## Contact
Feel free to contact me with any questions!

<!-- Optional -->
## License
Project is maintained under GNU GPL v.3 
<!-- This project is open source and available under the [... License](). -->

<!-- You don't have to include all sections - just the one's relevant to your project -->

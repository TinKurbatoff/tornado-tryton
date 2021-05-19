#!python3
from tornado_tryton import Tryton # class to connect to Tryton DB

import json
import logging

## Tornado webserver modules
from tornado.web import RequestHandler
from tornado.gen import coroutine # used for async execution in earlier version of Python 
from tornado.options import define, options # to access to a server-wide configuration 

##############################################
############# ENABLE LOGGING #################
##############################################
# create logger
logger = logging.getLogger(__name__)
logging.basicConfig(filename=__name__+'.log', 
                    level=logging.INFO, 
                    format = '%(asctime)s: /%(name)s/ %(levelname)s: %(message)s', 
                    datefmt='%m/%d/%Y %I:%M:%S %p')
logger.setLevel(logging.DEBUG) 
#######################################

TRYTON_CONFIG = '/etc/trytond.conf' # Check tryton doc for Tryton configuration details, access to Tryton DB is configured here 

############## TRYTON INTEGRATION #################
define('config', default={"TRYTON_DATABASE" : "tryton", "TRYTON_CONFIG" : TRYTON_CONFIG}, help='app config path')
logger.info(f'Using Tryton config file: { TRYTON_CONFIG }')
tryton = Tryton(options)
User = tryton.pool.get('res.user') # Important class type - User

@tryton.default_context # To create a default context of Tryton transactions
def default_context():
    return User.get_preferences(context_only=True)
## —————————————————————————————————————————————————————————


class CustomError(Exception): # Use for custom error handling, if needed
    pass

###########  RESPONDER FOR API REQUEST, HTML requests are handled in the same way.
class TrytonUser(RequestHandler):
    """Request for logging-in to Tryton"""
    SUPPORTED_METHODS = ("GET", "POST",)

    def jsonify(self, data, status=200):
        header = "Content-Type"
        body = "application/json"
        self.set_header(header, body)
        self.set_status(status)
        self.write(json.dumps(data))

    @tryton.transaction() ## To initiate tryton transaction and pass "local" request details 
    async def post(self, login, password):            
        logger.info(f"Request type: {self.request.method}")        
        logger.info('Login request...')
        # Check login and authorize
        user = User.search([('login', 'ilike', login)]) # Use `ilike` to ignore char case in login             
        if len(user)>0:
            # So, login is exist
            user, = User.search([('login', 'ilike', login)]) # to get the the first from the list if many
            logger.debug(f'Found user:{user.name}')
            logger.debug(f'Found user ID:{user.id}')
            parameters = {}
            parameters['password'] = password
            logger.debug(f'Tryton | Check password...')
            user_id = User.get_login(user.login, parameters) # bicrypt hash function
            if user_id:
                ## If user_id found — everyting is correct
                logger.info(f'Tryton | Success. Returned user ID:{user_id}') 
                return self.jsonify(data={"result" : "success"}, status = 200)
            else:
                ## If none found — password is incorrect
                logger.info('Tryton | Password was not accepted (no id in the response)')
                return self.jsonify({"result" : "wrong password"}, status=401)
        else:
            logger.info(f'Tryton | User not found: {login}')
            return self.jsonify({"result" : "unknown user"}, status=401)

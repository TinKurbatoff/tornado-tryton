# This file is part of tornado-tryton. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from functools import wraps

from tornado.options import define, options

from trytond import __version__ as trytond_version
from trytond.config import config

from trytond.exceptions import UserError, UserWarning, ConcurrencyException

trytond_version = tuple(map(int, trytond_version.split('.')))
__version__ = '1.0.1'
__all__ = ['Tryton', 'tryton_transaction']

def retry_transaction(retry):
    """Decorator to retry a transaction if failed. The decorated method
    will be run retry times in case of DatabaseOperationalError.
    """
    from trytond import backend
    from trytond.transaction import Transaction
    try:
        DatabaseOperationalError = backend.DatabaseOperationalError
    except AttributeError:
        DatabaseOperationalError = backend.get('DatabaseOperationalError')

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for count in range(retry, -1, -1):
                try:
                    return func(*args, **kwargs)
                except DatabaseOperationalError:
                    if count and not Transaction().readonly:
                        continue
                    raise
        return wrapper
    return decorator

class Tryton(object):
    "Control the Tryton integration to one or more Tornado applications."
    def __init__(self, app=None, configure_jinja=False):
        self.context_callback = None
        self.database_retry = None
        self.request_method = None
        self._configure_jinja = configure_jinja
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        "Initialize an application for the use with this Tryton setup."
        database = app.config.setdefault('TRYTON_DATABASE', None)
        user = app.config.setdefault('TRYTON_USER', 0)
        configfile = app.config.setdefault('TRYTON_CONFIG', None)

        config.update_etc(configfile)

        from trytond.pool import Pool
        from trytond.transaction import Transaction

        self.database_retry = config.getint('database', 'retry')
        self.pool = Pool(database)
        with Transaction().start(database, user, readonly=True):
            self.pool.init()

        if not hasattr(app, 'extensions'):
            define('extensions', default={}, help='extensions dict')
            # app.extensions = {}
        if not hasattr(app, 'url_map'):
            define('url_map', default={'converters': {}}, help='extensions dict')
            
        app.extensions['Tryton'] = self

    def default_context(self, callback):
        "Set the callback for the default transaction context"
        self.context_callback = callback
        return callback

    @property
    def language(self):
        "Return a language instance for the current request"
        from trytond.transaction import Transaction
        Lang = self.pool.get('ir.lang')
        # Do not use Transaction.language as it fallbacks to default language
        language = Transaction().context.get('language')
        if not language:
            language = request.accept_languages.best_match(
                Lang.get_translatable_languages())
        return Lang.get(language)

    def format_date(self, value, lang=None, *args, **kwargs):
        from trytond.report import Report
        if lang is None:
            lang = self.language
        return Report.format_date(value, lang, *args, **kwargs)

    def format_number(self, value, lang=None, *args, **kwargs):
        from trytond.report import Report
        if lang is None:
            lang = self.language
        return Report.format_number(value, lang, *args, **kwargs)

    def format_currency(self, value, currency, lang=None, *args, **kwargs):
        from trytond.report import Report
        if lang is None:
            lang = self.language
        return Report.format_currency(value, lang, currency, *args, **kwargs)

    def format_timedelta(
            self, value, converter=None, lang=None, *args, **kwargs):
        from trytond.report import Report
        if not hasattr(Report, 'format_timedelta'):
            return str(value)
        if lang is None:
            lang = self.language
        return Report.format_timedelta(
            value, converter=converter, lang=lang, *args, **kwargs)

    def _readonly(self):
        return not (self.request_method
            and self.request_method in ('PUT', 'POST', 'DELETE', 'PATCH'))

    def transaction(self, readonly=None, user=None, context=None):
        """Decorator to run inside a Tryton transaction.
        The decorated method could be run multiple times in case of
        database operational error.

        If readonly is None then the transaction will be readonly except for
        PUT, POST, DELETE and PATCH request methods.

        If user is None then TRYTON_USER will be used.

        readonly, user and context can also be callable.
        """
        from trytond import backend
        from trytond.cache import Cache
        from trytond.transaction import Transaction
        try:
            DatabaseOperationalError = backend.DatabaseOperationalError
        except AttributeError:
            DatabaseOperationalError = backend.get('DatabaseOperationalError')

        def get_value(value):
            return value() if callable(value) else value

        def instanciate(value):
            if isinstance(value, _BaseProxy):
                return value()
            return value

        def decorator(func):
            @retry_transaction(self.database_retry)
            @wraps(func)
            async def wrapper(*args, **kwargs):
                tryton = options.extensions['Tryton']
                tryton.request_method = args[0].request.method # what type of request was initiated
                database = options.config['TRYTON_DATABASE']
                if (5, 1) > trytond_version:
                    with Transaction().start(database, 0):
                        Cache.clean(database)
                if user is None:
                    transaction_user = get_value(
                        int(options.config['TRYTON_USER']))
                else:
                    transaction_user = get_value(user)

                transaction_context = {}
                if tryton.context_callback or context:
                    with Transaction().start(database, transaction_user,
                            readonly=True):
                        if tryton.context_callback:
                            transaction_context = tryton.context_callback()
                        transaction_context.update(get_value(context) or {})

                transaction_context.setdefault('_request', {}).update({
                        'remote_addr': args[0].request.remote_ip, # request.remote_addr,
                        'http_host': args[0].request.host, #  request.environ.get('HTTP_HOST'),
                        'scheme': args[0].request.protocol, # request.scheme,
                        'method': args[0].request.method, # GET, PUT or something else
                        'is_secure': True # —— DEBUG DEBUG DEBUG —— HTTPServerRequest. # HTTPServerRequest.get_secure_cookie,# request.is_secure,
                        })

                if readonly is None:
                    is_readonly = get_value(tryton._readonly)
                else:
                    is_readonly = get_value(readonly)

                # print(f"SECOND: {self.request_method}")

                with Transaction().start(database, transaction_user,
                        readonly=is_readonly,
                        context=transaction_context) as transaction:
                    try:
                        result = await func(*map(instanciate, args),
                            **dict((n, instanciate(v))
                                for n, v in kwargs.items()))
                        if (hasattr(transaction, 'cursor')
                                and not is_readonly):
                            transaction.cursor.commit()
                    except DatabaseOperationalError:
                        raise
                    except Exception as e:
                        if isinstance(e, (
                                    UserError,
                                    UserWarning,
                                    ConcurrencyException)):
                            raise BadRequest(e.message)
                        raise
                    if (5, 1) > trytond_version:
                        Cache.resets(database)
                from trytond.worker import run_task
                while transaction.tasks:
                    task_id = transaction.tasks.pop()
                    run_task(tryton.pool, task_id)
                return result
            return wrapper
        return decorator

tryton_transaction = Tryton.transaction

class _BaseProxy(object):
    pass

class _RecordsProxy(_BaseProxy):
    def __init__(self, model, ids):
        self.model = model
        self.ids = ids

    def __iter__(self):
        return iter(self.ids)

    def __call__(self):
        tryton = current_app.extensions['Tryton']
        Model = tryton.pool.get(self.model)
        return Model.browse(self.ids)


class _RecordProxy(_RecordsProxy):
    def __init__(self, model, id):
        super(_RecordProxy, self).__init__(model, [id])

    def __int__(self):
        return self.ids[0]

    def __call__(self):
        return super(_RecordProxy, self).__call__()[0]

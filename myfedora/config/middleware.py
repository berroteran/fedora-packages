"""Pylons middleware initialization"""
from beaker.middleware import SessionMiddleware, CacheMiddleware
from paste.cascade import Cascade
from paste.registry import RegistryManager
from paste.urlparser import StaticURLParser
from paste.deploy.converters import asbool
from pylons import config
from pylons.middleware import ErrorHandler, StaticJavascripts, \
    StatusCodeRedirect
from pylons.wsgiapp import PylonsApp
from routes.middleware import RoutesMiddleware

from tw.api import make_middleware as tw_middleware

from myfedora.config.environment import load_environment
from tg.ext.repoze.who.middleware import make_who_middleware
from myfedora.lib.middleware import FasMiddleware
from myfedora.lib.faswhoplugin import fas_make_who_middleware
from myfedora.model import User, Group, Permission, DBSession

# the criterion (ie instance of column) against which to mach
# the user name coming from a tentative login form
user_criterion = User.user_name
# the name of the column which is used as a unique identifier
user_id_col = 'user_id'

def make_app(global_conf, full_stack=True, **app_conf):
    """Create a Pylons WSGI application and return it

    ``global_conf``
        The inherited configuration for this application. Normally from
        the [DEFAULT] section of the Paste ini file.

    ``full_stack``
        Whether or not this application provides a full WSGI stack (by
        default, meaning it handles its own exceptions and errors).
        Disable full_stack when this application is "managed" by
        another WSGI middleware.

    ``app_conf``
        The application's local configuration. Normally specified in the
        [app:<name>] section of the Paste ini file (where <name>
        defaults to main).
    """
    # Configure the Pylons environment
    load_environment(global_conf, app_conf)

    # The Pylons WSGI app
    app = PylonsApp()

    # CUSTOM MIDDLEWARE HERE (filtered by error handling middlewares)

    # Routing/Session/Cache Middleware
    app = RoutesMiddleware(app, config['routes.map'])
    app = SessionMiddleware(app, config)
    app = CacheMiddleware(app, config)

    # ToscaWidgets Middleware
    app = tw_middleware(app, {
        # Change the following to 'mako' if using mako as a default template
        # language so widgets are displayed properly
        'toscawidgets.framework.default_view': 'genshi',
        })

    # Identity Middleware
    #app = make_who_middleware(app, config, User, user_criterion, user_id_col,
    #        DBSession)
    #app = FasMiddleware(app, config)
    app = fas_make_who_middleware(app, config)

    if asbool(full_stack):
        # Handle Python exceptions
        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])

        # Display error documents for 401, 403, 404 status codes (and
        # 500 when debug is disabled)
        if asbool(config['debug']):
            app = StatusCodeRedirect(app)
        else:
            app = StatusCodeRedirect(app, [400, 401, 403, 404, 500])

    # Establish the Registry for this application
    app = RegistryManager(app)

    # Static files (If running in production, and Apache or another web
    # server is handling this static content, remove the following 3 lines)
    javascripts_app = StaticJavascripts()
    static_app = StaticURLParser(config['pylons.paths']['static_files'])
    app = Cascade([static_app, javascripts_app, app])
    return app
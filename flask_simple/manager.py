"""Main Flask integration."""


from os import environ

import boto3

from flask import (
    _app_ctx_stack as stack,
)

from .errors import ConfigurationError
from .domain import Domain
from .sessions import SDBSessionInterface

class Simple(object):
    """SimpleDB wrapper for Flask."""

    DEFAULT_REGION = 'us-east-1'

    def __init__(self, app=None, domains=None):
        """
        Initialize this extension.

        :param obj app: The Flask application (optional).
        """
        self.app = app
        self.configured_domains = domains

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        Initialize this extension.

        :param obj app: The Flask application.
        """
        self.init_settings()
        self.check_settings()
        self.init_sessions()

    def init_sessions(self):
        self.app.session_interface = SDBSessionInterface(boto3.client('sdb'), "session", "")

    def init_settings(self):
        """Initialize all of the extension settings."""
        self.app.config.setdefault('SIMPLE_DOMAINS', [])

    def check_settings(self):
        """
        Check all user-specified settings to ensure they're correct.

        We'll raise an error if something isn't configured properly.

        If SIMPLE_DOMAINS isn't configured, just ignore

        :raises: ConfigurationError
        """
        pass

    @property
    def connection(self):
        """
        Our SimpleDB connection.

        This will be lazily created if this is the first time this is being
        accessed.  This connection is reused for performance.
        """
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, 'simple_connection'):
                ctx.simple_connection = boto3.client('sdb')

            return ctx.simple_connection

    @property
    def domains(self):
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, 'simple_domains'):
                ctx.simple_domains = {}
                for domain in self.configured_domains:
                    ctx.simple_domains[domain] = Domain(self.connection, domain)
            return ctx.simple_domains

    @property
    def domainsx(self):
        """
        Our SimpleDB domains.

        These will be lazily initializes if this is the first time the tables
        are being accessed.
        """
        ctx = stack.top
        if ctx is not None:
            if not hasattr(ctx, 'simple_domains'):
                ctx.simple_domains = {}
                domains = self.configured_domains or []
                domains = domains + self.app.config.get('SIMPLE_DOMAINS', [])
                for domain in domains:
                    ctx.simple_domains[domain] = Domain(self.connection, domain)

                    if not hasattr(ctx, 'simple_domain_%s' % domain):
                        setattr(ctx, 'simple_domain_%s' % domain, ctx.simple_domains[domain])

            return ctx.simple_domains

    def __getattr__(self, name):
        """
        Override the get attribute built-in method.

        This will allow us to provide a simple domain API.  Let's say a user
        defines two domains: `users` and `groups`.  In this case, our
        customization here will allow the user to access these domains by
        calling `simple.users` and `simple.groups`, respectively.

        :param str name: The SimpleDB domain name.
        :rtype: object
        :returns: A Domain object if the table was found.
        :raises: AttributeError on error.
        """
        if name in self.domains:
            return self.domains[name]

        raise AttributeError('No domain named %s found.' % name)

    def create_all(self):
        """
        Create all user-specified SimpleDB domains.

        We'll error out if the domains can't be created for some reason.
        """
        for name in self.app.config.get('SIMPLE_DOMAINS', []):
            self.connection.create_domain(DomainName=name)

    def destroy_all(self):
        """
        Destroy all user-specified SimpleDB domains.

        We'll error out if the domains can't be destroyed for some reason.
        """
        for name in self.app.config.get('SIMPLE_DOMAINS', []):
            self.connection.delete_domain(DomainName=name)

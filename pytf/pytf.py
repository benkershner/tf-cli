from .util import errmsg, outmsg
from ConfigParser import ConfigParser, NoSectionError
from argparse import ArgumentParser
from inspect import getargspec
from json import dumps
from os import environ
from os.path import expanduser
from re import match
from sys import exit, modules
import requests


class InvalidCredentialsError(Exception):
    def __init__(self, value='Unable to retrieve ThingFabric credentials.'):
        self.value = value

    def __str__(self):
        return repr(self.value)


class APIEndpoint(object):
    """
    API Endpoint Decorator
    """
    def __init__(self, group, argmetadata={}):
        self.group = group
        self.argmetadata = argmetadata

    def __call__(self, func):
        for prop in dir(self):
            if match('^_', prop):
                continue
            setattr(func, prop, getattr(self, prop))
        setattr(func, 'decorator', APIEndpoint)
        return func


class PyTF(object):
    _default_argmetadata = {
        'ttl': {
            'type': int,
            'help': 'TTL in seconds'},
        'account_id': {
            'help': 'ThingFabric account ID'},
        'email': {
            'help': 'new account email'},
        'password': {
            'help': 'new account password (plaintext)'},
        'project': {
            'help': 'new account project'},
        'username': {
            'help': 'new account user name'},
        'shouldBanOnAverage': {
            'action': 'store_true',
            'default': None,
            'help': 'ban account on limit overage'},
        'topic': {
            'help': 'MQTT topic'},
        'qos': {
            'type': int,
            'help': 'MQTT QoS (0, 1, or 2)'},
        'clientid': {
            'help': 'MQTT client ID'},
        'name': {
            'help': 'new name'},
        'description': {
            'help': 'new description'},
        'domain': {
            'help': 'domain'},
        'stuff': {
            'help': 'stuff'},
        'thing': {
            'help': 'thing'},
        'asJSON': {
            'action': 'store_true',
            'default': None,
            'help': 'return data as JSON'},
        'startDate': {
            'help': 'start date in YYYY-MM-DD format'},
        'endDate': {
            'help': 'end date in YYYY-MM-DD format'},
        'pagekey': {
            'help': 'pagekey'},
        'ignore_active': {
            'action': 'store_true',
            'default': None,
            'help': 'return all things (i.e. active and not active)'},
        'limit': {
            'help': 'number of things returned'},
        'whatever': {
            'help': 'whatever'},
        'attributes': {
            'metavar': 'ATTRIBUTE',
            'nargs': '+',
            'help': 'attributes (you can specify more than one)'}}

    def __init__(self, access_key=None, secret_key=None, url=None):
        config = ConfigParser()
        config.read(expanduser("~/.tf"))

        if access_key is None:
            if 'TF_ACCESS_KEY' in environ:
                access_key = environ['TF_ACCESS_KEY']
            else:
                try:
                    access_key = config.get('ThingFabric', 'access_key')
                except NoSectionError:
                    raise InvalidCredentialsError()

        if secret_key is None:
            if 'TF_SECRET_KEY' in environ:
                secret_key = environ['TF_SECRET_KEY']
            else:
                try:
                    secret_key = config.get('ThingFabric', 'secret_key')
                except NoSectionError:
                    raise InvalidCredentialsError()

        if url is None:
            if 'TF_URL' in environ:
                url = environ['TF_URL']
            else:
                try:
                    url = config.get('ThingFabric', 'url')
                except NoSectionError:
                    url = 'https://q.thingfabric.com/r/'

        self.access_key = access_key
        self.secret_key = secret_key
        self.url = url

    def _get_endpoints(self):
        """
        Get every annotated endpoint.
        """
        return {s: getattr(self, s)
                for s in dir(self)
                if hasattr(getattr(self, s), 'decorator')
                and getattr(self, s).decorator is APIEndpoint}

    def _get_endpoint_groups(self):
        """
        Get the endpoint groups.
        """
        return list(set([s.group for s in self._get_endpoints().values()]))

    def _request(self, request, uri, params=None):
        """
        Make the call to the ThingFabric API.
        """
        func = getattr(requests, request)

        data = None
        select = None
        if params is not None:
            # Data is special, so pop it out
            if 'data' in params:
                data = params['data']
                params.pop('data', None)

            if 'select' in params:
                data = params['select']
                params.pop('select', None)

            # Remove any params that were *not* set
            params = {key: params[key]
                      for key in params
                      if params[key] is not None}

        # Call Kelly Kapowski like what
        r = func('/'.join([self.url.strip('/'), uri.strip('/')]),
                 params=params,
                 data=data,
                 auth=(self.access_key, self.secret_key))

        try:
            result = r.json()
        except ValueError:
            result = r.text
        return (result, r.ok)

    def _print_help(self):
        """
        Print the usage in English.
        """
        endpoints = self._get_endpoints().keys()
        endpoints.sort()
        msg = "Available commands are:\n"
        msg += '\n'.join([' - %s' % cmd.replace('_', '-')
                          for cmd in endpoints])
        errmsg(msg)

    def _run_command(self, command, argv):
        """
        Run a given method by its name.
        """
        pretty_command = command.replace('_', '-')

        if command == 'help':
            self._print_help()
            return 1

        if command not in self._get_endpoints().keys():
            errmsg("'%s' is an invalid command." % pretty_command)
            return 1

        func = getattr(self, command)

        # Build the parser
        parser = ArgumentParser(prog='tf %s' % pretty_command, add_help=False)
        argspec = getargspec(getattr(self, command))
        for i, arg in enumerate(argspec.args):
            if arg == 'self':
                continue

            required = argspec.defaults is not None and \
                i < (len(argspec.args) - len(argspec.defaults))

            kwargs = {}
            if arg in self._default_argmetadata:
                kwargs.update(self._default_argmetadata[arg])
            if arg in func.argmetadata:
                kwargs.update(func.argmetadata[arg])

            parser.add_argument('--%s' % arg.replace('_', '-'),
                                required=required,
                                **kwargs)

        parser.add_argument('--select',
                            help='select a field from the response, in '
                                 'dot-notation (e.g. "foo.0.bar")')

        if len(argv) > 0 and argv[0] == 'help':
            parser.print_help()
            return 1

        parsed = parser.parse_args(argv)
        args = parsed._get_args()
        kwargs = dict(parsed._get_kwargs())
        select = kwargs.pop('select', None)
        (result, ok) = getattr(self, command)(*args, **kwargs)
        if select is not None:
            value = result
            for key in select.split('.'):
                value = value[key]
            outmsg(value)
        else:
            outmsg(dumps(result, indent=4))

        return 0 if ok else 1

    def main(self, argv):
        """
        Parse argv (the command line args) and run. Called by the CLI.
        """
        if len(argv) <= 1:
            self._print_help()
            return 1

        command = argv[1].lower().replace('-', '_')

        if command == 'help':
            self._print_help()
            return 1
        elif command in self._get_endpoints().keys():
            return self._run_command(command, argv[2:])
        else:
            errmsg("ERROR: '%s' is not a valid command\n" % command)
            self._print_help()
            return 1

    @APIEndpoint(group='auth')
    def get_token(self):
        return self._request('get', 'auth/token')

    @APIEndpoint(group='auth')
    def create_token(self, ttl=None):
        return self._request('post', 'auth/token', {'ttl': ttl})

    @APIEndpoint(group='accounts')
    def get_account(self, account_id):
        return self._request('get', 'accounts/%s' % account_id)

    @APIEndpoint(group='accounts')
    def create_account(self, email, password, project=None, username=None,
                       shouldBanOnAverage=None):
        return self._request('post', 'accounts',
                             {'email': email,
                              'password': password,
                              'project': project,
                              'username': username,
                              'shouldBanOnAverage': shouldBanOnAverage})

    @APIEndpoint(group='accounts')
    def update_account(self, email, password, username=None,
                       shouldBanOnAverage=None):
        return self._request('put', 'accounts',
                             {'email': email,
                              'password': password,
                              'username': username,
                              'shouldBanOnAverage': shouldBanOnAverage})

    @APIEndpoint(group='accounts')
    def delete_account(self, account):
        return self._request('delete', 'accounts/%s' % account)

    @APIEndpoint(group='mqtt')
    def publish(self, data, topic=None, qos=None, clientid=None):
        self._request('post', 'publish', {'data': data,
                                          'topic': topic,
                                          'qos': qos,
                                          'clientid': clientid})

    @APIEndpoint(group='projects')
    def get_all_projects(self):
        raise NotImplementedError()

    @APIEndpoint(group='projects')
    def get_project(self, project_id):
        self._request('get', 'projects/%s' % project_id)

    @APIEndpoint(group='projects')
    def create_project(self, name, description):
        self._request('post', 'projects', {'name': name,
                                           'description': description})

    @APIEndpoint(group='projects')
    def update_project(self, name):
        self._request('put', 'projects', {'name': name})

    @APIEndpoint(group='projects')
    def delete_project(self, project_id):
        self._request('delete', 'projects/%s' % project_id)

    @APIEndpoint(group='rules')
    def get_all_rules(self, domain=None, stuff=None, thing=None, asJSON=None):
        self._request('get', 'rules', {'domain': domain,
                                       'stuff': stuff,
                                       'thing': thing,
                                       'asJSON': asJSON})

    @APIEndpoint(group='rules')
    def get_rule(self, rule_id, asJSON=None):
        self._request('get', 'rules/%s' % rule_id, {'asJSON': asJSON})

    @APIEndpoint(group='rules')
    def create_rule(self, name, data, domain=None, stuff=None, thing=None,
                    description=None):
        self._request('post', 'rules', {'name': name,
                                        'data': data,
                                        'domain': domain,
                                        'stuff': stuff,
                                        'thing': thing,
                                        'description': description})

    @APIEndpoint(group='rules')
    def update_rule(self, name, data, domain=None, stuff=None, thing=None,
                    description=None):
        self._request('put', 'rules', {'name': name,
                                       'data': data,
                                       'domain': domain,
                                       'stuff': stuff,
                                       'thing': thing,
                                       'description': description})

    @APIEndpoint(group='rules')
    def delete_rule(self, rule_id):
        self._request('delete', 'rules/%s' % rule_id)

    @APIEndpoint(group='stats')
    def get_delivered_stats(self, startDate, endData=None):
        self._request('get', 'stats/delivered', {'startDate': startDate,
                                                 'endDate': endDate})

    @APIEndpoint(group='stats')
    def get_published_stats(self, startDate, endData=None):
        self._request('get', 'stats/published', {'startDate': startDate,
                                                 'endDate': endDate})

    @APIEndpoint(group='sql')
    def get_all_rules(self):
        self._request('get', 'sql')

    @APIEndpoint(group='sql')
    def get_rule(self, rule_id):
        self._request('get', 'sql/%s' % rule_id)

    @APIEndpoint(group='sql')
    def create_rule(self):
        self._request('post', 'sql')

    @APIEndpoint(group='sql')
    def delete_rule(self, rule_id):
        self._request('delete', 'sql/%s' % rule_id)

    @APIEndpoint(group='sql')
    def create_rule_integration(self, rule_id):
        self._request('post', 'sql/%s/integrations' % rule_id)

    @APIEndpoint(group='sql')
    def delete_rule_integration(self, rule_id, integration_id=None):
        if integration_id is None:
            uri = 'sql/%s/integrations' % rule_id
        else:
            uri = 'sql/%s/integrations/%s' % (rule_id, integration_id)
        self._request('delete', uri)

    @APIEndpoint(group='things')
    def get_all_things(self, pagekey=None, ignore_active=None, limit=None):
        active = None
        if ignore_active is not None:
            active = not ignore_active
        self._request('get', 'things', {'pagekey': pagekey,
                                        'active': active,
                                        'limit': limit})

    @APIEndpoint(group='things')
    def create_thing(self, domain=None, stuff=None, name=None,
                     description=None):
        self._request('post', 'things', {'domain': domain,
                                         'stuff': stuff,
                                         'name': name,
                                         'description': description})

    @APIEndpoint(group='things')
    def delete_thing(self, thing_name, domain=None, stuff=None):
        self._request('delete', 'things/%s' % thing_name, {'domain': domain,
                                                           'stuff': stuff})

    @APIEndpoint(group='things')
    def get_present_thing(self, thing_name, domain=None, stuff=None,
                          whatever=None):
        uri = 'things/%s/present' % thing_name
        self._request('get', uri, {'domain': domain,
                                   'stuff': stuff,
                                   'whatever': whatever})

    @APIEndpoint(group='things')
    def get_past_thing(self, thing_name, domain=None, stuff=None,
                       attributes=None):
        if attributes is not None:
            attributes = ','.join(attributes)
        uri = 'things/%s/past' % thing_name
        self._request('get', uri, {'domain': domain,
                                   'stuff': stuff,
                                   'attributes': attributes})

    @APIEndpoint(group='things')
    def get_thing_count(self, domain=None):
        self._request('get', 'things/count', {'domain': domain})

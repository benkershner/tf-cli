# tf-cli
Because `curl`ing is for Canadians.

`tf-cli` provides a Python module (`pytf`) that includes a command line tool
(`tf`) that wraps the 2lemetry ThingFabric API. At this point in time, both
`tf-cli` and the ThingFabric APIv3 are both *heavily* in beta, so there should
be plenty of caution, at least until `tf-cli` gets a 1.0 release.

The command line tool is heavily inspired by the the AWS CLI, so if you're
familiar with that, this is an easy tool to pick up.

##### Installation
The easiest way to install is using `pip`:

    $ sudo pip install pytf

If you'd like to install from the Github repository itself (in order to do
some development, etc.), simply clone it, use `virtualenv` to set up the
environment, and hack away.

    $ git clone https://www.github.com/benkershner/tf-cli
    $ cd tf-cli
    $ virtualenv venv
    $ source venv/bin/activate
    (venv)$ python ./setup.py develop

After you've installed `pytf` the first thing you *should* do is set up your
ThingFabric credentials file. This will contain your `access_key` and your
`secret_key`. Create a file in `~/.tf` and fill it in with your credentials:

    [ThingFabric]
    access_key = 01234567-89ab-cdef-0123-456789abcdef
    secret_key = fedcba98-7654-3210-fedc-ba9876543210
    url = https://q.thingfabric.com/r/

If you do not set your credentials here, the tool with attempt to read
`TF_ACCESS_KEY` and `TF_SECRET_KEY` from the environment. If this fails, it'll
throw a fit. Also note that you *do not* have to set the ThingFabric API URL
here; if you omit it, it will just fall back to this URL. If you'd rather use
the test URL or not use HTTPS (not recommended, dummies), then set it here.

##### Command Line Usage
The easiest way to see what `tf` can do is to just ask it:

    $ tf help

This will generate a list of all of the available commands. These *roughly*
map one-to-one to the ThingFabric APIv3. I took a few liberties to create a
consistent naming convention and overloaded a function or two where I could.
That said, it's not rocket surgery.

To take a look at what an invdiviual command can do, just ask it:

    $ tf get-present-thing help

The arguments listed *roughly* map to one-to-one to the APIv3 arguments.
Again, liberties were taken.

The command will result in the JSON response from the normal API call, and
will exit 0 if the command succeded and exit 1 if not. There's also a cute
option, `--select`, that's available on each command which allows you to
select a particular item out of the JSON response.

    $ tf nested-command-response
    {
        "foo": [
            {
                "bar": "rab",
                "baz": "zab"
            }
        ]
    }
    $ tf nested-command-response --select foo.0.bar
    rab

##### Module Usage
The CLI is generated directly from annotations in the module itself, so most
of the documentation can be gathered from that. It's should be easy enough
to understand, though documentation on PyPI will be coming soon(ish). Short
of that the source code, REPL, `dir`, and `inspect.getargspec` are always
your friends :)

    from pytf import PyTF
    
    api = PyTF(access_key, secret_key)
    (result, ok) = api.create_token(ttl=3600)
    token = result['authToken']

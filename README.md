# electrum-aionostr

asyncio nostr client

```
Free software: BSD license
Original Author: Dave St.Germain
Fork Author/Maintainer: The Electrum Developers
Language: Python (>= 3.8)
```


[![Latest PyPI package](https://badge.fury.io/py/electrum-aionostr.svg)](https://pypi.org/project/electrum-aionostr/)
[![Build Status](https://api.cirrus-ci.com/github/spesmilo/aionostr.svg?branch=electrum)](https://cirrus-ci.com/github/spesmilo/aionostr)


This is a fork of aionostr that does not require Coincurve


## Features

* Retrieve anything from the nostr network, using one command:

```
$ aionostr get nprofile1qqsv0knzz56gtm8mrdjhjtreecl7dl8xa47caafkevfp67svwvhf9hcpz3mhxue69uhkgetnvd5x7mmvd9hxwtn4wvspak3h
$ aionostr get -v nevent1qqsxpnzhw2ddf2uplsxgc5ctr9h6t65qaalzvzf0hvljwrz8q64637spp3mhxue69uhkyunz9e5k75j6gxm
$ aionostr query -s -q '{"kinds": [1], "limit":10}'
$ aionostr send --kind 1 --content test --private-key <privatekey>
$ aionostr mirror -r wss://source.relay -t wss://target.relay --verbose '{"kinds": [4]}'
```


Set environment variables:

```
NOSTR_RELAYS=wss://brb.io,wss://nostr.mom
NOSTR_KEY=`aionostr gen | head -1`
```


## Credits

This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter)
and the [audreyr/cookiecutter-pypackage](https://github.com/audreyr/cookiecutter-pypackage) project template.

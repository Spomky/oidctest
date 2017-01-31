#!/usr/bin/env python3
import os

import cherrypy
import logging
from oic.utils import webfinger
from oidctest.cp.op import Provider
from oidctest.cp.op import WebFinger
from oidctest.cp.op_handler import OPHandler
from oidctest.cp.test_list import TestList
from oidctest.cp.log_handler import ClearLog
from oidctest.cp.log_handler import Log
from oidctest.cp.log_handler import Tar
from oidctest.cp.setup import cb_setup

from otest.flow import Flow
from otest.prof_util import SimpleProfileHandler


logger = logging.getLogger("")
LOGFILE_NAME = 'rp_test.log'
hdlr = logging.FileHandler(LOGFILE_NAME)
base_formatter = logging.Formatter(
    "%(asctime)s %(name)s:%(levelname)s %(message)s")

hdlr.setFormatter(base_formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)


def named_kc(config, iss):
    _kc = config.KEYDEFS[:]
    for kd in _kc:
        if 'key' in kd:
            kd['key'] = iss
    return _kc


if __name__ == '__main__':
    import argparse
    from oidctest.rp import provider

    parser = argparse.ArgumentParser()
    parser.add_argument('-b', dest='bundle', required=True)
    parser.add_argument('-d', dest='debug', action='store_true')
    parser.add_argument('-f', dest='flowsdir', required=True)
    parser.add_argument('-i', dest='iss', required=True)
    parser.add_argument('-k', dest='insecure', action='store_true')
    parser.add_argument('-p', dest='port', default=80, type=int)
    parser.add_argument('-P', dest='path')
    parser.add_argument('-s', dest='sign_key', required=True)
    parser.add_argument('-t', dest='tls', action='store_true')
    parser.add_argument(dest="config")
    args = parser.parse_args()

    _com_args, _op_arg, config = cb_setup(args)

    folder = os.path.abspath(os.curdir)
    _flows = Flow(args.flowsdir, profile_handler=SimpleProfileHandler)
    op_handler = OPHandler(provider.Provider, _op_arg, _com_args, _flows)

    cherrypy.config.update(
        {'environment': 'production',
         'log.error_file': 'site.log',
         'tools.trailing_slash.on': False,
         'server.socket_host': '0.0.0.0',
         'log.screen': True,
         'tools.sessions.on': True,
         'tools.encode.on': True,
         'tools.encode.encoding': 'utf-8'
         })

    provider_config = {
        '/': {
            'root_path': 'localhost',
            'log.screen': True,
        },
        '/static': {
            'tools.staticdir.dir': os.path.join(folder, 'static'),
            'tools.staticdir.debug': True,
            'tools.staticdir.on': True,
            'log.screen': True
        }}

    # WebFinger
    webfinger_config = {'/': {'base_url': _op_arg['baseurl']}}
    cherrypy.tree.mount(WebFinger(webfinger.WebFinger()),
                        '/.well-known/webfinger', webfinger_config)

    # test list
    cherrypy.tree.mount(
        TestList('flows', 'links.json',
                 'List of OIDC RP library tests for profile: "<i>{}</i>"',
                 config.GRPS),
        '/list')

    log_root = folder + '/log'

    cherrypy.tree.mount(Log(log_root), '/log')
    cherrypy.tree.mount(ClearLog(log_root), '/clear')
    cherrypy.tree.mount(Tar(log_root), '/mktar')

    # OIDC Providers
    cherrypy.tree.mount(Provider(op_handler, _flows), '/', provider_config)

    # If HTTPS
    if args.tls:
        cherrypy.server.ssl_certificate = config.SERVER_CERT
        cherrypy.server.ssl_private_key = config.SERVER_KEY

    cherrypy.engine.start()
    cherrypy.engine.block()
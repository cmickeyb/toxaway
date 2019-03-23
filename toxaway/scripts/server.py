#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import argparse

import pdo.common.config as pconfig
import pdo.common.keys as keys
import pdo.common.logger as plogger

import pdo.eservice.pdo_helper as pdo_enclave_helper
import toxaway.views

import logging
logger = logging.getLogger(__name__)

## XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
## XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
from twisted.web import http
from twisted.web.static import File
from twisted.web.resource import Resource, NoResource
from twisted.web.server import Site
from twisted.python.threadpool import ThreadPool
from twisted.internet import reactor, defer
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.web.wsgi import WSGIResource

## ----------------------------------------------------------------
def ErrorResponse(request, error_code, msg) :
    """Generate a common error response for broken requests
    """

    result = ""
    if request.method != 'HEAD' :
        result = msg + '\n'
        result = result.encode('utf8')

    request.setResponseCode(error_code)
    request.setHeader(b'Content-Type', b'text/plain')
    request.setHeader(b'Content-Length', len(result))
    request.write(result)

    try :
        request.finish()
    except :
        logger.exception("exception during request finish")
        raise

    return request

## XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
## XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class ShutdownResource(Resource) :
    isLeaf = True

    ## -----------------------------------------------------------------
    def __init__(self) :
        Resource.__init__(self)

    ## -----------------------------------------------------------------
    def render_GET(self, request) :
        logger.warn('shutdown request received')
        reactor.callLater(1, reactor.stop)

        return ErrorResponse(request, http.NO_CONTENT, "shutdown")

# -----------------------------------------------------------------
# -----------------------------------------------------------------
def StartService(config) :
    try :
        http_port = config['Service']['HttpPort']
        http_host = config['Service']['Host']
        worker_threads = config['Service'].get('WorkerThreads', 8)
        reactor_threads = config['Service'].get('ReactorThreads', 8)
    except KeyError as ke :
        logger.error('missing configuration for %s', str(ke))
        sys.exit(-1)

    logger.info('service started on port %s', http_port)

    thread_pool = ThreadPool(maxthreads=worker_threads)
    thread_pool.start()
    reactor.addSystemEventTrigger('before', 'shutdown', thread_pool.stop)

    flask_app = toxaway.views.register(config)
    flask_site = WSGIResource(reactor, reactor.getThreadPool(), flask_app)

    root = Resource()
    root.putChild(b'shutdown', ShutdownResource())
    root.putChild(b'flask', flask_site)

    files = config.get('StaticContent', {})
    logger.info('files=%s', files)
    for key, val in files.items() :
        logger.info('map <%s> to <%s>', key, val)
        root.putChild(key.encode(), File(val.encode()))

    site = Site(root, timeout=60)
    site.displayTracebacks = True

    reactor.suggestThreadPoolSize(reactor_threads)

    endpoint = TCP4ServerEndpoint(reactor, http_port, backlog=32, interface=http_host)
    endpoint.listen(site)

# -----------------------------------------------------------------
# -----------------------------------------------------------------
def RunService() :
    @defer.inlineCallbacks
    def shutdown_twisted():
        logger.info("Stopping Twisted")
        yield reactor.callFromThread(reactor.stop)

    reactor.addSystemEventTrigger('before', 'shutdown', shutdown_twisted)

    try :
        reactor.run()
    except ReactorNotRunning:
        logger.warn('shutdown')
    except :
        logger.warn('shutdown')

    sys.exit(0)

# -----------------------------------------------------------------
# -----------------------------------------------------------------
def LocalMain(config) :
    StartService(config)
    RunService()

## XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
## XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX

## -----------------------------------------------------------------
ContractHost = os.environ.get("HOSTNAME", "localhost")
ContractHome = os.environ.get("PDO_HOME") or os.path.realpath("/opt/pdo")
ContractEtc = os.path.join(ContractHome, "etc")
ContractKeys = os.path.join(ContractHome, "keys")
ContractLogs = os.path.join(ContractHome, "logs")
ContractData = os.path.join(ContractHome, "data")
LedgerURL = os.environ.get("PDO_LEDGER_URL", "http://127.0.0.1:8008/")
ScriptBase = os.path.splitext(os.path.basename(sys.argv[0]))[0]

config_map = {
    'base' : ScriptBase,
    'data' : ContractData,
    'etc'  : ContractEtc,
    'home' : ContractHome,
    'host' : ContractHost,
    'keys' : ContractKeys,
    'logs' : ContractLogs,
    'ledger' : LedgerURL
}

# -----------------------------------------------------------------
# -----------------------------------------------------------------
def Main() :
    # parse out the configuration file first
    conffiles = [ 'toxaway.toml' ]
    confpaths = [ ".", "./etc", ContractEtc ]

    parser = argparse.ArgumentParser()

    parser.add_argument('--config', help='configuration file', nargs = '+')
    parser.add_argument('--config-dir', help='directory to search for configuration files', nargs = '+')

    parser.add_argument('--identity', help='Identity to use for the process', required = True, type = str)

    parser.add_argument('--logfile', help='Name of the log file, __screen__ for standard output', type=str)
    parser.add_argument('--loglevel', help='Logging level', type=str)

    options = parser.parse_args()

    # first process the options necessary to load the default configuration
    if options.config :
        conffiles = options.config

    if options.config_dir :
        confpaths = options.config_dir

    global config_map
    config_map['identity'] = options.identity

    try :
        config = pconfig.parse_configuration_files(conffiles, confpaths, config_map)
    except pconfig.ConfigurationException as e :
        logger.error(str(e))
        sys.exit(-1)

    # set up the logging configuration
    if config.get('Logging') is None :
        config['Logging'] = {
            'LogFile' : '__screen__',
            'LogLevel' : 'INFO'
        }
    if options.logfile :
        config['Logging']['LogFile'] = options.logfile
    if options.loglevel :
        config['Logging']['LogLevel'] = options.loglevel.upper()

    plogger.setup_loggers(config.get('Logging', {}))
    sys.stdout = plogger.stream_to_logger(logging.getLogger('STDOUT'), logging.DEBUG)
    sys.stderr = plogger.stream_to_logger(logging.getLogger('STDERR'), logging.WARN)

    # GO!
    LocalMain(config)

## -----------------------------------------------------------------
## Entry points
## -----------------------------------------------------------------
Main()

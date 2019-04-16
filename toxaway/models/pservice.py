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

import base64
import glob
import hashlib
import json
import os

from pdo.common.keys import EnclaveKeys
from pdo.service_client.provisioning import ProvisioningServiceClient

import logging
logger = logging.getLogger(__name__)

# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class ProvisioningServiceList(object) :
    """A class to store information about a set of enclave services
    """

    # -----------------------------------------------------------------
    @classmethod
    def load(cls, config) :
        """Compute a list of URLs for known enclave services
        """
        root = ProvisioningService.__root_directory__(config)
        pservice_files = glob.glob('{0}/*.json'.format(root))

        pservice_list = cls(config)
        for pservice_file in pservice_files :
            pservice = ProvisioningService.load(config, pservice_file, use_raw=True)
            pservice_list.add(pservice)

        return pservice_list

    # -----------------------------------------------------------------
    def __init__(self, config) :
        self.config = config
        self.__by_url__ = {}
        self.__by_identity__ = {}

    # -----------------------------------------------------------------
    def __iter__(self) :
        for url, pservice in self.__by_url__.items() :
            yield pservice

    # -----------------------------------------------------------------
    def urls(self) :
        return self.__by_url__.keys()

    # -----------------------------------------------------------------
    def identities(self) :
        return self.__by_identity__.keys()

    # -----------------------------------------------------------------
    def get_by_url(self, url) :
        return self.__by_url__[url]

    # -----------------------------------------------------------------
    def get_by_service_id(self, service_id) :
        url = self.__by_identity__[service_id]
        return self.__by_url__[url]

    # -----------------------------------------------------------------
    def add(self, pservice) :
        self.__by_identity__[pservice.service_id] = pservice.service_url
        self.__by_url__[pservice.service_url] = pservice

    # -----------------------------------------------------------------
    @property
    def count(self) :
        return len(self.__by_url__)


# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class ProvisioningService(object) :
    """A class to store information about an enclave service
    """
    # -----------------------------------------------------------------
    @staticmethod
    def __root_directory__(config) :
        """Pull the enclave service data directory from the
        configuration file.
        """
        path_config = config.get('ContentPaths', {})
        return os.path.realpath(path_config.get('PService', os.path.join(os.environ['HOME'], '.toxaway')))

    # -----------------------------------------------------------------
    @staticmethod
    def __file_name__(config, pservice_id) :
        """create the name of the file for storing the profile
        """
        root = ProvisioningService.__root_directory__(config)
        pservice_id = pservice_id.replace('+','-').replace('/','_')
        return os.path.realpath(os.path.join(root, '{0}.json'.format(os.path.basename(pservice_id))))

    # -----------------------------------------------------------------
    @classmethod
    def create(cls, config, service_url, name=None) :
        """create a new pservice from a URL and save it
        """

        try :
            logger.info('create pservice for %s', service_url)
            pservice_client = ProvisioningServiceClient(service_url)
        except :
            logger.warn('failed to retrieve pservice information')
            return None

        logger.warn('verifying key: %s', pservice_client.verifying_key)
        psinfo = pservice_client.get_public_info()
        logger.warn('pspk: %s', psinfo['pspk'])

        pservice_object = cls()
        pservice_object.service_url = service_url
        pservice_object.service_key = pservice_client.verifying_key
        pservice_object.file_name = hashlib.sha256(pservice_client.verifying_key.encode('utf8')).hexdigest()[:16]
        pservice_object.name = name

        pservice_object.save(config)

        return pservice_object

    # -----------------------------------------------------------------
    @classmethod
    def load(cls, config, file_name, use_raw=False) :
        """load an existing pservice from disk
        """
        logger.info('load pservice %s', file_name)
        if not use_raw :
            file_name = ProvisioningService.__file_name__(config, file_name)

        if not os.path.exists(file_name) :
            logger.info('profile file does not exist: %s', file_name)
            return None

        with open(file_name, "rb") as pf:
            serialized_pservice = pf.read()

        logger.info('pservice loaded from file %s', file_name)
        return cls(serialized_pservice)

    # -----------------------------------------------------------------
    def __init__(self, serialized_pservice = None) :
        if serialized_pservice :
            self.deserialize(serialized_pservice)
        else :
            self.service_key = None
            self.service_url = None
            self.file_name = None
            self.name = None

    # -----------------------------------------------------------------
    @property
    def service_id(self) :
        return self.service_key

    # -----------------------------------------------------------------
    def save(self, config) :
        """serialize the pservice, encrypt it and write it to disk
        """
        serialized_pservice = self.serialize()
        file_name = ProvisioningService.__file_name__(config, self.file_name)

        pservice_dir = os.path.dirname(file_name)
        if not os.path.isdir(pservice_dir) :
            os.makedirs(pservice_dir)

        with open(file_name, "wb") as pf:
            pf.write(serialized_pservice)

        logger.info('pservice saved to %s', file_name)

    # -----------------------------------------------------------------
    def deserialize(self, serialized_pservice) :
        """deserialize the pservice
        """
        try :
            serialized_pservice = serialized_pservice.decode('utf-8')
        except AttributeError :
            pass

        serialized = json.loads(serialized_pservice)

        self.service_url = serialized['service_url']
        self.service_key = serialized['service_key']
        self.file_name = serialized['file_name']
        self.name = serialized.get('name')

    # -----------------------------------------------------------------
    def serialize(self) :
        """serialize the pservice for writing to disk
        """
        serialized = dict()
        serialized['service_url'] = self.service_url
        serialized['service_key'] = self.service_key
        serialized['file_name'] = self.file_name
        if self.name :
            serialized['name'] = self.name

        return json.dumps(serialized).encode('utf-8')

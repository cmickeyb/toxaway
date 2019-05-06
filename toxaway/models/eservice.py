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
from pdo.service_client.enclave import EnclaveServiceClient
from sawtooth.helpers import pdo_connect

import logging
logger = logging.getLogger(__name__)

# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class EnclaveServiceList(object) :
    """A class to store information about a set of enclave services
    """

    # -----------------------------------------------------------------
    @classmethod
    def load(cls, config) :
        """Compute a list of URLs for known enclave services
        """
        root = EnclaveService.__root_directory__(config)
        eservice_files = glob.glob('{0}/*.json'.format(root))

        eservice_list = cls(config)
        for eservice_file in eservice_files :
            eservice = EnclaveService.load_from_file(config, eservice_file)
            eservice_list.add(eservice)

        return eservice_list

    # -----------------------------------------------------------------
    def __init__(self, config) :
        self.config = config
        self.__by_url__ = {}
        self.__by_identity__ = {}

    # -----------------------------------------------------------------
    def __iter__(self) :
        for url, eservice in self.__by_url__.items() :
            yield eservice

    # -----------------------------------------------------------------
    def urls(self) :
        return self.__by_url__.keys()

    # -----------------------------------------------------------------
    def identities(self) :
        return self.__by_identity__.keys()

    # -----------------------------------------------------------------
    def get_by_url(self, enclave_url) :
        return self.__by_url__[enclave_url]

    # -----------------------------------------------------------------
    def get_by_enclave_id(self, enclave_id) :
        enclave_url = self.__by_identity__[enclave_id]
        return self.__by_url__[enclave_url]

    # -----------------------------------------------------------------
    def add(self, eservice) :
        self.__by_identity__[eservice.enclave_id] = eservice.enclave_service_url
        self.__by_url__[eservice.enclave_service_url] = eservice

    # -----------------------------------------------------------------
    @property
    def count(self) :
        return len(self.__by_url__)

# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class EnclaveService(object) :
    """A class to store information about an enclave service
    """
    # -----------------------------------------------------------------
    @staticmethod
    def __root_directory__(config) :
        """Pull the enclave service data directory from the
        configuration file.
        """
        path_config = config.get('ContentPaths', {})
        return os.path.realpath(path_config.get('EService', os.path.join(os.environ['HOME'], '.toxaway')))

    # -----------------------------------------------------------------
    @staticmethod
    def __file_name__(config, eservice_id) :
        """create the name of the file for storing the profile
        """
        root = EnclaveService.__root_directory__(config)
        eservice_id = eservice_id.replace('+','-').replace('/','_')
        return os.path.realpath(os.path.join(root, '{0}.json'.format(os.path.basename(eservice_id))))

    # -----------------------------------------------------------------
    @classmethod
    def create(cls, config, eservice_url, name=None) :
        """create a new eservice from a URL and save it
        """

        try :
            logger.info('create eservice for %s', eservice_url)
            eservice_client = EnclaveServiceClient(eservice_url)
            enclave_info = eservice_client.get_enclave_public_info()
            enclave_id = enclave_info['enclave_id']
        except :
            logger.warn('failed to retrieve eservice information')
            return None

        try :
            ledger_config = config["Sawtooth"]
            client = pdo_connect.PdoRegistryHelper(ledger_config['LedgerURL'])
            enclave_ledger_info = client.get_enclave_dict(enclave_id)
        except Exception as e :
            logger.info('error getting enclave; %s', str(e))
            raise Exception('failed to retrieve enclave; {}'.format(enclave_id))

        eservice_object = cls()
        eservice_object.enclave_service_url = eservice_url
        eservice_object.storage_service_url = enclave_info['storage_service_url']
        eservice_object.enclave_keys = EnclaveKeys(enclave_info['verifying_key'], enclave_info['encryption_key'])
        eservice_object.file_name = eservice_object.enclave_keys.hashed_identity
        eservice_object.name = name or eservice_url

        eservice_object.enclave_owner_id = enclave_ledger_info['owner_id']
        eservice_object.registration_block_id = enclave_ledger_info['last_registration_block_context']
        eservice_object.registration_transaction_id = enclave_ledger_info['registration_transaction_id']
        eservice_object.proof_data = enclave_ledger_info['proof_data']

        assert eservice_object.enclave_id == enclave_info['enclave_id']

        eservice_object.save(config)

        return eservice_object

    # -----------------------------------------------------------------
    @classmethod
    def load_from_file(cls, config, eservice_file_name) :
        """load an existing eservice from disk
        """
        logger.debug('load eservice from file %s', eservice_file_name)

        if not os.path.exists(eservice_file_name) :
            return None

        with open(eservice_file_name, "rb") as pf:
            serialized_eservice = pf.read()

        eservice_object = cls(serialized_eservice)
        eservice_object.file_name = eservice_file_name

        return eservice_object

    # -----------------------------------------------------------------
    @classmethod
    def load(cls, config, eservice_id) :
        """load an existing eservice from disk
        """
        logger.debug('load eservice from identity %s', eservice_id)
        eservice_file_name = EnclaveService.__file_name__(config, eservice_id)
        return cls.load_from_file(config, eservice_file_name)

    # -----------------------------------------------------------------
    def __init__(self, serialized_eservice = None) :
        self.__eservice_client__ = None

        if serialized_eservice :
            self.deserialize(serialized_eservice)
        else :
            self.enclave_keys = None
            self.enclave_service_url = None
            self.storage_service_url = None

    # -----------------------------------------------------------------
    @property
    def eservice_id(self) :
        return self.enclave_keys.hashed_identity

    # -----------------------------------------------------------------
    @property
    def enclave_id(self) :
        return self.enclave_keys.identity

    # -----------------------------------------------------------------
    @property
    def printable_txn_id(self) :
        result = []
        for x in range(0, len(self.registration_transaction_id), 50) :
            result.append(self.registration_transaction_id[x:x+50])
        return "\n".join(result)

    # -----------------------------------------------------------------
    @property
    def eservice_client(self) :
        if self.__eservice_client__ is None :
            self.__eservice_client__ = EnclaveServiceClient(self.enclave_service_url)

        return self.__eservice_client__

    # -----------------------------------------------------------------
    def save(self, config) :
        """serialize the eservice, encrypt it and write it to disk
        """
        serialized_eservice = self.serialize()
        eservice_file = EnclaveService.__file_name__(config, self.file_name)

        eservice_dir = os.path.dirname(eservice_file)
        if not os.path.isdir(eservice_dir) :
            os.makedirs(eservice_dir)

        with open(eservice_file, "wb") as pf:
            pf.write(serialized_eservice)

        logger.debug('eservice saved to %s', eservice_file)

    # -----------------------------------------------------------------
    def deserialize(self, serialized_eservice) :
        """deserialize the eservice
        """
        try :
            serialized_eservice = serialized_eservice.decode('utf-8')
        except AttributeError :
            pass

        eservice_info = json.loads(serialized_eservice)

        self.name = eservice_info['name']
        self.enclave_service_url = eservice_info['enclave_service_url']
        self.storage_service_url = eservice_info['storage_service_url']
        self.enclave_keys = EnclaveKeys(
            eservice_info['enclave_keys']['verifying_key'], eservice_info['enclave_keys']['encryption_key'])

        self.enclave_owner_id = eservice_info['enclave_owner_id']
        self.registration_block_id = eservice_info['registration_block_id']
        self.registration_transaction_id = eservice_info['registration_transaction_id']
        self.proof_data = eservice_info['proof_data']

    # -----------------------------------------------------------------
    def serialize(self) :
        """serialize the eservice for writing to disk
        """
        serialized = dict()
        serialized['name'] = self.name
        serialized['enclave_service_url'] = self.enclave_service_url
        serialized['storage_service_url'] = self.storage_service_url
        serialized['enclave_keys'] = self.enclave_keys.serialize()
        serialized['enclave_owner_id'] = self.enclave_owner_id
        serialized['registration_block_id'] = self.registration_block_id
        serialized['registration_transaction_id'] = self.registration_transaction_id
        serialized['proof_data'] = self.proof_data

        return json.dumps(serialized).encode('utf-8')

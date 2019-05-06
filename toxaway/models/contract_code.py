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

from pdo.contract import ContractCode as pdo_contract_code

import logging
logger = logging.getLogger(__name__)

# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class ContractCodeList(object) :
    """A class to store information about contract code files
    """

    # -----------------------------------------------------------------
    @classmethod
    def load(cls, config) :
        """Compute a list of URLs for known contracts
        """
        root = ContractCode.__root_directory__(config)
        ccode_files = glob.glob('{0}/*.json'.format(root))

        ccode_list = cls(config)
        for ccode_file in ccode_files :
            ccode = ContractCode.load(config, ccode_file, use_raw=True)
            ccode_list.add(ccode)

        return ccode_list

    # -----------------------------------------------------------------
    def __init__(self, config) :
        self.config = config
        self.__by_name__ = {}
        self.__by_hash__ = {}

    # -----------------------------------------------------------------
    def __iter__(self) :
        for code_hash, ccode in self.__by_hash__.items() :
            yield ccode

    # -----------------------------------------------------------------
    def hashes(self) :
        return self.__by_hash__.keys()

    # -----------------------------------------------------------------
    def names(self) :
        return self.__by_name__.keys()

    # -----------------------------------------------------------------
    def get_by_name(self, name) :
        code_hash = self.__by_name__[name]
        return self.__by_hash__[code_hash]

    # -----------------------------------------------------------------
    def get_by_hash(self, code_hash) :
        return self.__by_hash__[code_hash]

    # -----------------------------------------------------------------
    def add(self, ccode) :
        self.__by_name__[ccode.name] = ccode.code_hash
        self.__by_hash__[ccode.code_hash] = ccode

    # -----------------------------------------------------------------
    @property
    def count(self) :
        return len(self.__by_hash__)

# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class ContractCode(object) :
    """A class to store information about an enclave service
    """
    # -----------------------------------------------------------------
    @staticmethod
    def __root_directory__(config) :
        """Pull the enclave service data directory from the
        configuration file.
        """
        path_config = config.get('ContentPaths', {})
        return os.path.realpath(path_config.get('ContractCode', os.path.join(os.environ['HOME'], '.toxaway')))

    # -----------------------------------------------------------------
    @staticmethod
    def __file_name__(config, ccode_id) :
        """create the name of the file for storing the profile
        """
        root = ContractCode.__root_directory__(config)
        return os.path.realpath(os.path.join(root, '{0}.json'.format(os.path.basename(ccode_id))))

    # -----------------------------------------------------------------
    @staticmethod
    def __data_file_name__(config, ccode_id) :
        """create the name of the file for storing the profile
        """
        root = ContractCode.__root_directory__(config)
        return os.path.realpath(os.path.join(root, '{0}.scm'.format(os.path.basename(ccode_id))))

    # -----------------------------------------------------------------
    @classmethod
    def create(cls, config, code_file, code_name) :
        """create a new contract code object and save it
        """

        try :
            code_data = code_file.read()
        except :
            logger.warn('failed to retrieve ccode information')
            return None

        ccode_object = cls()
        ccode_object.name = code_name
        ccode_object.code_hash = hashlib.sha256(code_data).hexdigest()[:16]
        ccode_object.data_file_name = ContractCode.__data_file_name__(config, ccode_object.code_hash)

        code_path = os.path.dirname(ccode_object.data_file_name)
        if not os.path.isdir(code_path) :
            os.makedirs(code_path)

        with open(ccode_object.data_file_name, "wb") as df :
            df.write(code_data)

        ccode_object.save(config)

        return ccode_object

    # -----------------------------------------------------------------
    @classmethod
    def load(cls, config, code_file_name, use_raw=False) :
        """load an existing ccode from disk
        """
        if not use_raw :
            code_file_name = ContractCode.__file_name__(config, code_file_name)
        if not os.path.exists(code_file_name) :
            return None

        with open(code_file_name, "rb") as pf:
            serialized = pf.read()

        return cls(serialized)

    # -----------------------------------------------------------------
    def __init__(self, serialized = None) :
        self.__data__ = None
        if serialized :
            self.deserialize(serialized)
        else :
            self.name = None
            self.code_hash = None
            self.data_file_name = None

    # -----------------------------------------------------------------
    def create_pdo_contract(self) :
        return pdo_contract_code(self.code, self.name)

    # -----------------------------------------------------------------
    @property
    def code(self) :
        if self.__data__ is None :
            logger.debug('read contract code from file %s', self.data_file_name)
            with open(self.data_file_name, "rb") as df :
                self.__data__ = df.read()

        return self.__data__.decode()

    # -----------------------------------------------------------------
    def save(self, config) :
        """serialize the ccode, encrypt it and write it to disk
        """
        serialized = self.serialize()
        code_file_name = ContractCode.__file_name__(config, self.code_hash)

        code_path = os.path.dirname(code_file_name)
        if not os.path.isdir(code_path) :
            os.makedirs(code_path)

        with open(code_file_name, "wb") as pf:
            pf.write(serialized)

        logger.debug('ccode saved to %s', code_file_name)

    # -----------------------------------------------------------------
    def deserialize(self, serialized) :
        """deserialize the ccode
        """
        try :
            serialized = serialized.decode('utf-8')
        except AttributeError :
            pass

        code_info = json.loads(serialized)

        self.name = code_info['name']
        self.code_hash = code_info['code_hash']
        self.data_file_name = code_info['data_file_name']

    # -----------------------------------------------------------------
    def serialize(self) :
        """serialize the ccode for writing to disk
        """
        serialized = dict()
        serialized['name'] = self.name
        serialized['code_hash'] = self.code_hash
        serialized['data_file_name'] = self.data_file_name

        return json.dumps(serialized).encode('utf-8')

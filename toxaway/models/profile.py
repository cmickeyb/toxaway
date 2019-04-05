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

import glob
import json
import os

from pdo.common.keys import ServiceKeys
import pdo.common.crypto as crypto

import logging
logger = logging.getLogger(__name__)

# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
class Profile(object) :
    """A class to store profile information
    """
    # -----------------------------------------------------------------
    @staticmethod
    def __profile_root_directory__(config) :
        path_config = config.get('ContentPaths', {})
        return os.path.realpath(path_config.get('Profile', os.path.join(os.environ['HOME'], '.toxaway')))

    # -----------------------------------------------------------------
    @staticmethod
    def __profile_file_name__(config, profile) :
        """create the name of the file for storing the profile
        """
        profile_root = Profile.__profile_root_directory__(config)
        return os.path.realpath(os.path.join(profile_root, '{0}.enc'.format(os.path.basename(profile))))

    # -----------------------------------------------------------------
    @staticmethod
    def __encryption_key__(password) :
        """create an AES encryption/decryption key from the password
        """
        try :
            password = password.encode('utf-8')
        except AttributeError :
            pass

        return crypto.compute_message_hash(password)[:16]

    # -----------------------------------------------------------------
    @staticmethod
    def list_profiles(config) :
        profile_root = Profile.__profile_root_directory__(config)
        profile_files = glob.glob('{0}/*.enc'.format(profile_root))
        return list(map(lambda f : os.path.basename(f), profile_files))

    # -----------------------------------------------------------------
    @classmethod
    def create(cls, config, profile_name, password) :
        """create a new profile and save it
        """
        logger.info('create profile for %s', profile_name)
        profile_object = cls(profile_name)
        profile_object.save(config, password)

        return profile_object

    # -----------------------------------------------------------------
    @classmethod
    def load(cls, config, profile_name, password) :
        """load an existing profile from disk
        """
        logger.info('load profile for %s', profile_name)
        profile_file = Profile.__profile_file_name__(config, profile_name)
        if not os.path.exists(profile_file) :
            return None

        with open(profile_file, "rb") as pf:
            encrypted_profile = pf.read()

        logger.info('profile loaded from %s', profile_file)

        skenc_key = Profile.__encryption_key__(password)
        serialized_profile = crypto.SKENC_DecryptMessage(skenc_key, encrypted_profile)
        serialized_profile = bytes(serialized_profile)

        return cls(profile_name, serialized_profile)

    # -----------------------------------------------------------------
    def __init__(self, name, serialized_profile = None) :
        self.name = name
        if serialized_profile :
            self.deserialize(serialized_profile)
        else :
            self.keys = ServiceKeys.create_service_keys()

    # -----------------------------------------------------------------
    def save(self, config, password) :
        """serialize the profile, encrypt it and write it to disk
        """
        serialized_profile = self.serialize()
        skenc_key = Profile.__encryption_key__(password)

        encrypted_profile = crypto.SKENC_EncryptMessage(skenc_key, serialized_profile)
        encrypted_profile = bytes(encrypted_profile)

        profile_file = Profile.__profile_file_name__(config, self.name)
        profile_dir = os.path.dirname(profile_file)
        if not os.path.isdir(profile_dir) :
            os.makedirs(profile_dir)

        with open(profile_file, "wb") as pf:
            pf.write(encrypted_profile)

        logger.info('profile saved to %s', profile_file)

    # -----------------------------------------------------------------
    def deserialize(self, serialized_profile) :
        """deserialize the profile
        """
        try :
            serialized_profile = serialized_profile.decode('utf-8')
        except AttributeError :
            pass

        profile_data = json.loads(serialized_profile)

        pem_encoded_signing_key = profile_data.get('signing_key')
        self.keys = ServiceKeys(crypto.SIG_PrivateKey(pem_encoded_signing_key))

    # -----------------------------------------------------------------
    def serialize(self) :
        """serialize the profile for writing to disk
        """
        serialized = dict()
        serialized['signing_key'] = self.keys.signing_key

        return json.dumps(serialized).encode('utf-8')

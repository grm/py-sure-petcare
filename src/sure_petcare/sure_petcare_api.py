import os
import pickle
import uuid

import requests

from enum import Enum

CACHE_FILE_PATH = os.path.expanduser("~/.surepet.cache")


class Event(Enum):
    MOVE = 0
    BAT_WARN = 1
    LOCK_ST = 6
    MOVE_UID = 7
    USR_IFO = 12
    USR_NEW = 17
    CURFEW = 20


class Mod(Enum):
    UNLOCKED = 0
    LOCKED_IN = 1
    LOCKED_OUT = 2
    LOCKED_ALL = 3
    CURFEW = 4
    CURFEW_LOCKED = -1
    CURFEW_UNLOCKED = -2
    CURFEW_UNKNOWN = -3


class ProductId(Enum):
    ROUTER = 1
    FLAP = 3


class Locations(Enum):
    UNKNOWN = -1
    INSIDE = 1
    OUTSIDE = 2


class SurePetApi:
    """Class to take care of network communication with SurePet's products."""

    API_USER_AGENT = (
        "Mozilla/5.0 (Linux; Android 7.0; SM-G930F Build/NRD90M; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Version/4.0 Chrome/64.0.3282.137 Mobile Safari/537.36"
    )

    def __init__(
        self, email_address=None, password=None, cache_file=CACHE_FILE_PATH, debug=False
    ):
        """
        `email_address` and `password` are self explanatory.  They are cached on
        disc file `cache_file` and are therefore only mandatory on first
        invocation (or if either have been changed).

        Cache
        -----

        This API makes aggressive use of caching.  This is not optional
        because use of this API must never be responsible for more impact on
        Sure's servers than the official app.

        In order to ensure that the cache is written back to disc, instances of
        this class must be used as a context manager.  Any API call that could
        change cache state *can only* be called from within a context block.

        The cache is written out at the end of the context block.  You can
        continue to query the API outside of the context block, but any attempt
        to update or modify anything will result in exception SPAPIReadOnly.

        Example:
        ```
        with SurePetFlap() as api:
            api.update_pet_status()
        for pet_id, info in api.pets.items():
            print( '%s is %s' % (info['name'], api.get_pet_location(pet_id),) )
        ```

        Note that the disc copy of the cache is locked while in context, so
        update what you need and leave context as soon as possible.
        """
        # cache_status is None to indicate that it hasn't been initialised
        self.cache_file = cache_file or CACHE_FILE_PATH
        self.cache_lockfile = self.cache_file + ".lock"
        self._init_email = email_address
        self._init_pw = password
        # self._load_cache()
        self.__read_only = True
        if (email_address is None or password is None) and self.cache[
            "AuthToken"
        ] is None:
            raise ValueError("No cached credentials and none provided")
        self.debug = debug
        self.s = requests.session()
        if self.cache["device_id"] is None:
            self.device_id = str(uuid.uuid4())
        else:
            self.device_id = self.cache["device_id"]
        if debug:
            self.req_count = self.req_rx_bytes = 0
            self.s.hooks["response"].append(self._log_req)

    def _load_cache(self):
        """
        Read cache file.  The cache is written by the context `__exit__()`
        method.
        """
        # Cache locking is done by the context manager methods.
        try:
            with open(self.cache_file, "rb") as f:
                self.cache = pickle.load(f)
        except (pickle.PickleError, OSError):
            self.cache = {
                "AuthToken": None,
                "households": None,
                "default_household": self._init_default_household,
                "router_status": {},  # indexed by household
                "flap_status": {},  # indexed by household
                "pet_status": {},  # indexed by household
                "pet_timeline": {},  # indexed by household
                "house_timeline": {},  # indexed by household
                "version": 1,  # of cache structure.
                "device_id": None,
            }

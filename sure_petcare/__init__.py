#!/usr/bin/python3
"""
Access the sure petcare access information
"""

import json
import requests
from datetime import datetime, timedelta
import sure_petcare.utils as utils
from .utils import mk_enum

DIRECTION ={0:'Looked through',1:'Entered House',2:'Left House'}
INOUT_STATUS = {1 : 'Inside', 2 : 'Outside'}

# The following event types are known, eg EVT.CURFEW.
EVT = mk_enum( 'EVT',
               {'MOVE': 0,
                'MOVE_UID': 7, # movement of unknown animal
                'LOCK_ST': 6,
                'USR_IFO': 12,
                'USR_NEW': 17,
                'CURFEW': 20,
                } )

LK_MOD = mk_enum( 'LK_MOD',
                  {'UNLOCKED': 0,
                   'LOCKED_IN': 1,
                   'LOCKED_OUT': 2,
                   'LOCKED_ALL': 3,
                   'CURFEW': 4,
                   'CURFEW_LOCKED': -1,
                   'CURFEW_UNLOCKED': -2,
                   'CURFEW_UNKNOWN': -3,
                   } )

PROD_ID = mk_enum( 'PROD_ID',
                   {'ROUTER': 1,
                    'FLAP': 3,
                    } )

LOC = mk_enum( 'LOC',
               {'INSIDE': 1,
                'OUTSIDE': 2,
                'UNKNOWN': -1,
                } )


# REST API endpoints (no trailing slash)
_URL_AUTH = 'https://app.api.surehub.io/api/auth/login'
_URL_HOUSEHOLD = 'https://app.api.surehub.io/api/household'
_URL_DEV = 'https://app.api.surehub.io/api/device'
_URL_TIMELINE = 'https://app.api.surehub.io/api/timeline'
_URL_PET = 'https://app.api.surehub.io/api/pet'

API_USER_AGENT = 'Mozilla/5.0 (Linux; Android 7.0; SM-G930F Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/64.0.3282.137 Mobile Safari/537.36'


class SurePetFlapAPI(object):
    """Class to take care of network communication with SurePet's products.

    Unless you want to parse data from Sure directly, instantiate SurePetFlap()
    rather than this class directly.  The constructor arguments are the same as
    below.
    """

    def __init__(self, email_address=None, password=None, household_id=None, device_id=None, cache=None, debug=False):
        """
        `email_address` and `password` are self explanatory.  They are
        mandatory if a populated `cache` object is not supplied.

        `household_id` need only be specified if your account has access to more
        than one household and you know its ID.  You can find out which is which
        by examining property `households`.

        You can set the default household after the fact by assigning the
        appropriate ID to property `default_household` if the initial default
        is not to your liking.  This assignment will persist in the cache, so
        you only need do it the once.  Do not set it to None or you will get
        exceptions.

        `device_id` is the ID of *this* client.  If none supplied, a plausible,
        unique-ish default is supplied.

        `cache` is the persistent object cache that allows subsequent instances
        function with minimal, if any, additional Sure server API calls.

        You *should* always preserve the cache and pass it back to new
        instances whereever possible.  Amongst performance and cost benefits,
        it also means you don't need to supply your email and password again
        unless they change.

        Unless supplied with a populated `cache` object, the new instance
        remains unpopulated (and unusable) until method `update()` has been
        called.
        """
        if (email_address is None or password is None) and cache is None:
            raise ValueError('Please provide, email, password and device id')
        self.debug=debug
        self.s = requests.session()
        if debug:
            self.req_count = self.req_rx_bytes = 0
            self.s.hooks['response'].append( self._log_req )
        if device_id is None:
            self.device_id = utils.gen_device_id()
        else:
            self.device_id = device_id
        if cache is None:
            self.cache = {'AuthToken': None,
                          'households': None,
                          'default_household': household_id,
                          'router_status': {}, # indexed by household
                          'flap_status': {}, # indexed by household
                          'pet_status': {}, # indexed by household
                          'pet_timeline': {}, # indexed by household
                          'house_timeline': {}, # indexed by household
                          'curfew_locked': {}, # indexed by household
                          }
        else:
            self.cache = cache
        # Always override email/pw, if supplied
        if email_address:
            self.cache['email'] = email_address
        if password:
            self.cache['pw'] = password

    @property
    def default_household( self ):
        """
        Get the default house ID.
        """
        return self.cache['default_household']
    @default_household.setter
    def default_household( self, id ):
        """
        Set the default household ID.
        """
        self.cache['default_household'] = id
    @property
    def households( self ):
        """
        Return dict of households which include name, timezone information
        suitable for use with pytz and also pet info.

        NB: Indexed by household ID.
        """
        return self.cache['households']
    @households.setter
    def households( self, data ):
        """
        Set household data.
        """
        self.cache['households'] = data
    @property
    def router_status( self ):
        return self.cache['router_status']
    @property
    def flap_status( self ):
        return self.cache['flap_status']
    @property
    def pet_status( self ):
        return self.cache['pet_status']
    @property
    def pet_timeline( self ):
        return self.cache['pet_timeline']
    @property
    def house_timeline( self ):
        return self.cache['house_timeline']
    @property
    def curfew_locked( self ):
        return self.cache['curfew_locked']

    def get_default_router( self, hid ):
        """
        Set the default router ID.
        """
        return self.households[hid]['default_router']
    def set_default_router( self, hid, rid ):
        """
        Get the default router ID.
        """
        self.households[hid]['default_router'] = rid

    def get_default_flap( self, hid ):
        """
        Get the default flap ID.
        """
        return self.households[hid]['default_flap']
    def set_default_flap( self, hid, fid ):
        """
        Set the default flap ID.
        """
        self.households[hid]['default_flap'] = fid

    def get_pets( self, hid = None ):
        """
        Return dict of pets.  Default household used if not specified.
        """
        hid = hid or self.default_household
        return self.households[hid]['pets']

    def get_pet_id_by_name(self, name, household_id = None):
        """
        Returns the numeric ID (not the tag ID) of the pet by name.  Match is
        case insensitive and the first pet found with that name is returned.
        Default household used if not specified.
        """
        household_id = household_id or self.default_household
        for petid, petdata in self.households[household_id]['pets'].items():
            if petdata['name'].lower() == name.lower():
                return petid

    def get_lock_mode(self, flap_id = None, household_id = None):
        """
        Returns one of enum LK_MOD indicating flap lock mode.  Default household
        and flap used if not specified.
        """
        household_id = household_id or self.default_household
        household = self.households[household_id]
        if flap_id is None:
            flap_id = household['default_flap']
        mode = self.flap_status[household_id][flap_id]['locking']['mode']
        if mode == LK_MOD.CURFEW:
            if self.curfew_locked[household_id] is None:
                mode = LK_MOD.CURFEW_UNKNOWN
            elif self.curfew_locked[household_id]:
                mode = LK_MOD.CURFEW_LOCKED
            else:
                mode = LK_MOD.CURFEW_UNLOCKED
        return mode

    def get_pet_location(self, pet_id, household_id = None):
        """
        Returns one of enum LOC indicating last known movement of the pet.
        Default household used if not specified.
        """
        household_id = household_id or self.default_household
        if pet_id not in self.pet_status[household_id]:
            raise SPAPIUnknownPet()
        return self.pet_status[household_id][pet_id]['where']

    def update(self):
        """
        Update everything.  MUST be invoked immediately after instance creation
        unless cache was supplied.
        """
        self.update_authtoken()
        self.update_households()
        self.update_device_ids()
        self.update_pet_info()
        self.update_pet_timeline()
        self.update_pet_status()
        self.update_flap_status()
        #self.update_router_status()
        # XXX For now, router status contains little of interest and isn't worth
        #     the API call.
        self.update_house_timeline()

    def update_authtoken(self, force = False):
        """
        Update cache with authentication token if missing.  Use `force = True`
        when the token expires (the API generally does this automatically).
        """
        if self.cache['AuthToken'] is not None and not force:
            return
        data = {"email_address": self.cache['email'],
                "password": self.cache['pw'],
                "device_id": self.device_id,
                }
        headers=self._create_header()
        response = self.s.post(_URL_AUTH, headers=headers, json=data)
        if response.status_code == 401:
            raise SPAPIAuthError()
        response_data = response.json()
        self.cache['AuthToken'] = response_data['data']['token']

    def update_households(self, force = False):
        """
        Update cache with info about the household(s) associated with the account.
        """
        if self.households is not None and not force:
            return
        params = ( # XXX Could we merge update_households() with update_pet_info()?
            ('with[]', ['household', 'timezone',],), #'pet',
        )
        headers=self._create_header()
        response_household = self._api_get(_URL_HOUSEHOLD, headers=headers, params=params)
        response_household = response_household.json()
        self.households = {
            x['id']: {'name': x['name'],
                      'olson_tz': x['timezone']['timezone'],
                      'utc_offset':  x['timezone']['utc_offset'],
                      'default_router': None,
                      'default_flap': None,
                      } for x in response_household['data']
            }
        # default_household may have been set by the constructor, but override
        # it anyway if the specified ID wasn't in the data just fetched.
        if self.default_household not in self.households:
            self.default_household = response_household['data'][0]['id']

    def update_device_ids(self, hid = None, force = False):
        """
        Update cache with list of router and flap IDs for each household.  The
        default router and flap are set to the first ones found.
        """
        hid = hid or self.default_household
        household = self.households[hid]
        if (household['default_router'] is not None and
            household['default_flap'] is not None and not force):
            return
        params = (
            ('with[]', 'children'),
        )
        routers = household['routers'] = []
        flaps = household['flaps'] = []
        url = '%s/%s/device' % (_URL_HOUSEHOLD, hid,)
        response_children = self._get_data(url, params)
        for device in response_children['data']:
            if device['product_id'] == PROD_ID.FLAP: # Catflap
                flaps.append( device['id'] )
            elif device['product_id'] == PROD_ID.ROUTER: # Router
                routers.append( device['id'] )
        household['default_flap'] = flaps[0]
        household['default_router'] = routers[0]

    def update_pet_info(self, hid = None, force = False):
        """
        Update cache with pet information.
        """
        hid = hid or self.default_household
        household = self.households[hid]
        if household.get('pets') is not None and not force:
            return
        params = (
            ('with[]', ['photo', 'tag']),
        )
        url = '%s/%s/pet' % (_URL_HOUSEHOLD, hid,)
        response_pets = self._get_data(url, params)
        household['pets'] = {
            x['id']: {'name': x['name'],
                      'tag_id': x['tag_id'],
                      'photo': x.get('photo', {}).get('location')
                      } for x in response_pets['data']
            }

    def update_flap_status(self, hid = None):
        """
        Update flap status.  Default household used if not specified.
        """
        hid = hid or self.default_household
        household = self.households[hid]
        for fid in household['flaps']:
            url = '%s/%s/status' % (_URL_DEV, fid,)
            response = self._get_data(url)
            self.cache['flap_status'].setdefault( hid, {} )[fid] = response['data']

    def update_router_status(self, hid = None):
        """
        Update router status.  Don't call unless you really need to because
        there's not much of interest here.  Default household used if not
        specified.
        """
        hid = hid or self.default_household
        household = self.households[hid]
        for rid in household['routers']:
            url = '%s/%s/status' % (_URL_DEV, rid,)
            response = self._get_data(url)
            self.cache['router_status'].setdefault( hid, {} )[rid] = response['data']

    def update_house_timeline(self, hid = None):
        """
        Update household event timeline and curfew lock status.  Default
        household used if not specified.
        """
        hid = hid or self.default_household
        params = (
            ('type', '0,3,6,7,12,13,14,17,19,20'),
        )
        url = '%s/household/%s' % (_URL_TIMELINE, hid,)
        response = self._get_data(url, params)
        htl = self.cache['house_timeline'][hid] = response['data']
        curfew_events = [x for x in htl if x['type'] == EVT.CURFEW]
        if curfew_events:
            # Serialised JSON within a serialised JSON structure?!  Weird.
            self.cache['curfew_locked'][hid] = json.loads(curfew_events[0]['data'])['locked']
        else:
            # new accounts might not be populated with the relevent information
            self.cache['curfew_locked'][hid] = None

    def update_pet_status(self, hid = None):
        """
        Update pet status.  Default household used if not specified.
        """
        hid = hid or self.default_household
        self.cache['pet_status'][hid] = {}
        for pid in self.get_pets( hid ):
            url = '%s/%s/position' % (_URL_PET, pid,)
            headers = self._create_header()
            response = self._get_data(url)
            self.cache['pet_status'][hid][pid] = response['data']

    def update_pet_timeline(self, hid = None):
        """
        Update pet timeline.  Default household used if not specified.
        """
        hid = hid or self.default_household
        household = self.households[hid]
        params = (
            ('type', '0,3,6,7,12,13,14,17,19,20'),
        )
        petdata={}
        for pid in household['pets']:
            url = '%s/pet/%s/%s' % (_URL_TIMELINE, pid, hid,)
            response = self._get_data(url, params=params)
            petdata[pid] = response['data']
        self.cache['pet_timeline'][hid] = petdata

    def _get_data(self, url, params=None, refresh_interval=3600):
        headers = None
        if url in self.cache:
            time_since_last =  datetime.now() - self.cache[url]['ts']
            if time_since_last.total_seconds() < refresh_interval:
                # Use cached data but check freshness with ETag
                headers = self._create_header(ETag=self.cache[url]['ETag'])
            else:
                # Ignore cached data and force refresh
                self._debug_print('Forcing refresh of data for %s' % (url,))
        else:
            self.cache[url]={}
        if headers is None:
            headers = self._create_header()
        response = self._api_get(url, headers=headers, params=params)
        if response.status_code in [304, 500, 502, 503, 504,]:
            # Used cached data in event of (respectively), not modified, server
            # error, server overload, server unavailable and gateway timeout
            return self.cache[url]['LastData']
        self.cache[url]['LastData'] = response.json()
        self.cache[url]['ETag'] = response.headers['ETag'][1:-1]
        self.cache[url]['ts'] = datetime.now()
        return self.cache[url]['LastData']

    def _create_header(self, ETag=None):
        headers={
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://surepetcare.io',
            'User-Agent': API_USER_AGENT,
            'Referer': 'https://surepetcare.io/',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en-GB;q=0.9',
            'X-Requested-With': 'com.sureflap.surepetcare',
        }

        if self.cache['AuthToken'] is not None:
            headers['Authorization']='Bearer ' + self.cache['AuthToken']
        if ETag is not None:
            headers['If-None-Match'] = ETag
        return headers

    def _api_get( self, url, *args, **kwargs ):
        r = self.s.get( url, *args, **kwargs )
        if r.status_code == 401:
            # Retry once
            self.update_authtoken( force = True )
            if 'headers' in kwargs and 'Authorization' in kwargs['headers']:
                kwargs['headers']['Authorization']='Bearer ' + self.cache['AuthToken']
                r = self.s.get( url, *args, **kwargs )
            else:
                raise SPAPIException( 'Auth required but not present in header' )
        return r

    def _debug_print(self, string):
        if self.debug:
            print(string)

    def _log_req( self, r, *args, **kwargs ):
        """
        Debugging aid: print network requests
        """
        l = len( '\n'.join( ': '.join(x) for x in r.headers.items() ) )
        l += len(r.content)
        self.req_count += 1
        self.req_rx_bytes += l
        print( 'requests: %s %s -> %s (%0.3f kiB, total %0.3f kiB in %s requests)' % (r.request.method, r.request.url, r.status_code, l/1024.0, self.req_rx_bytes/1024.0, self.req_count,) )


class SurePetFlapMixin( object ):
    """
    A mixin that implements introspection of data collected by SurePetFlapAPI.
    """

    def print_timeline(self, pet_id, entry_type = None, household_id = None):
        """
        Print timeline for a particular pet, specify entry_type to only get one
        direction.  Default household is used if not specified.
        """
        household_id = household_id or self.default_household
        household = self.households[household_id]
        try:
            tag_id = household['pets'][pet_id]['tag_id']
            pet_name = household['pets'][pet_id]['name']
        except KeyError as e:
            raise SPAPIUnknownPet( str(e) )
        petdata = self.pet_timeline[household_id][pet_id]

        for movement in petdata:
            if movement['type'] in [EVT.MOVE_UID, EVT.LOCK_ST, EVT.USR_IFO, EVT.USR_NEW, EVT.CURFEW]:
                continue
            try:
                if entry_type is not None:
                    if movement['movements'][0]['tag_id'] == tag_id:
                        if movement['movements'][0]['direction'] == entry_type:
                            print(movement['movements'][0]['created_at'], pet_name, DIRECTION[movement['movements'][0]['direction']])
                else:
                    if movement['movements'][0]['tag_id'] == tag_id:
                        print(movement['movements'][0]['created_at'], pet_name, DIRECTION[movement['movements'][0]['direction']])
            except Exception as e:
                print(e)

    def locked(self, flap_id = None, household_id = None):
        """
        Return whether door is locked or not.  Default household and flap used
        if not specified.
        """
        household_id = household_id or self.default_household
        household = self.households[household_id]
        if flap_id is None:
            flap_id = household['default_flap']
        lock = self.flap_status[household_id][flap_id]['locking']['mode']
        if lock == LK_MOD.UNLOCKED:
            return False
        if lock in [LK_MOD.LOCKED_IN, LK_MOD.LOCKED_OUT, LK_MOD.LOCKED_ALL,]:
            return True
        if lock == LK_MOD.CURFEW:
            if self.curfew_locked[household_id]:
                return True
            else:
                return False

    def lock_mode(self, flap_id = None, household_id = None):
        """
        Returns a string describing the flap lock mode.  Default household and
        flap used if not specified.
        """
        lock = self.get_lock_mode( flap_id, household_id )
        if lock == LK_MOD.UNLOCKED:
            return 'Unlocked'
        elif lock == LK_MOD.LOCKED_IN:
            return 'Keep pets in'
        elif lock == LK_MOD.LOCKED_OUT:
            return 'Keep pets out'
        elif lock == LK_MOD.LOCKED_ALL:
            return 'Locked'
        elif lock == LK_MOD.CURFEW_UNKNOWN:
            return 'Curfew enabled but state unknown'
        elif lock == LK_MOD.CURFEW_LOCKED:
            return 'Locked with curfew'
        elif lock == LK_MOD.CURFEW_UNLOCKED:
            return 'Unlocked with curfew'

    def get_current_status(self, petid=None, name=None, household_id = None):
        """
        Returns a string describing the last known movement of the pet.

        Note that because sometimes the chip reader fails to read the pet
        (especially if they exit too quickly), this function can indicate that
        they're inside when in fact they're outside.  The same limitation
        presumably applies to the official website and app.
        """
        if petid is None and name is None:
            raise ValueError('Please define petid or name')
        if petid is None:
            petid = self.get_pet_id_by_name(name)
        petid=int(petid)
        loc = get_pet_location( pet_id, household_id )
        if loc == LOC.UNKNOWN:
            return 'Unknown'
        else:
            #Get last update
            return INOUT_STATUS[loc]


class SurePetFlap(SurePetFlapMixin, SurePetFlapAPI):
    """Class to take care of network communication with SurePet's products.

    See docstring for parent classes on how to use.  In particular, **please**
    do preserve property `cache` between instantiations in order to minimise
    wasted requests to Sure's servers.

    `cache` is guaranteed to be pickleable but not guaranteed to be
    serialisable as JSON.  How you store and retrieve it is up to you.

    """
    pass


class SPAPIException( Exception ):
    pass


class SPAPIAuthError( SPAPIException ):
    pass


class SPAPIUnknownPet( SPAPIException ):
    pass

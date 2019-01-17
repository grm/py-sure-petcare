from enum import Enum


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

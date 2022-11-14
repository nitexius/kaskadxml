from .klogger_xml import KloggerXML
from .klogic_xml import KlogicXML
from .alarms_xml import AlarmsXML
from .alrm import alrm, stations, xo_choices
from .indices import indices as i, constants as c, smart_divide_all_n
from .exceptions import (
    ErrorMissingProduct,
    ErrorCentralAlarm,
    ErrorMissingNofflTag,
    KlogicBadFormatError,
    KloggerBadFormatError,
    AlarmsBadFormatError,
    NotEnoughVar,
    NewTagsError,
    DefaultAlarmError
)

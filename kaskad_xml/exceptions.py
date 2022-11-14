class ErrorMissingProduct(Exception):
    """ Исключение при отсутствующих тегах nofll у контроллера"""


class ErrorCentralAlarm(Exception):
    """ Исключение при отсутствующих авариях у централей 351, 551"""


class ErrorMissingNofflTag(Exception):
    """ Исключение при отсутствующих тегах nofll у контроллера"""


class KlogicBadFormatError(Exception):
    """Klogic XML: Неправильный формат"""


class KloggerBadFormatError(Exception):
    """Klogger XML: Неправильный формат"""


class AlarmsBadFormatError(Exception):
    """Klogger XML: Неправильный формат"""


class NotEnoughVar(Exception):
    """В группе Alarms у централи добавлены не все переменные"""


class NewTagsError(Exception):
    """Новые переменные"""


class DefaultAlarmError(Exception):
    """Шаблон Alarm XML не найден"""

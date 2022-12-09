from dgu.models import Dgu_tag
from dgu.kaskad_xml import KlogicXML, AlarmsXML
from .new_tags_tools import get_new_tags, save_new_tags
from kaskadxml.kaskad_xml import NewTagsError, AlarmsBadFormatError
from kaskadxml.log_utils import logger
from kaskadxml.tools import create_output_file


def update_klogic_xml(klogic_xml: KlogicXML):
    new_tags = get_new_tags(klogic_xml)
    if len(new_tags):
        save_new_tags(new_tags)
        raise NewTagsError(f'Новые переменные: {len(new_tags)}')
    else:
        return create_output_file(klogic_xml)


def update_alarms_xml(alarm_xml: AlarmsXML, args):
    try:
        logger.debug(alarm_xml.group_item.tag)
        alarm_xml.set_alarm_xml(args.klogic_xml, Dgu_tag.get_alarm_tags())
        return create_output_file(alarm_xml)
    except AttributeError:
        raise AlarmsBadFormatError('Alarm XML: Неправильный формат')
    
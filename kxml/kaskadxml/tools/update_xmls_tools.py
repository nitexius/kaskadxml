from kaskadxml.models import Tag
from kaskadxml.kaskad_xml import (
    KlogicXML,
    KloggerXML,
    AlarmsXML,
    MnemoListXML,
    GM_MnemoXML,
    NewTagsError,
    KloggerBadFormatError,
    AlarmsBadFormatError
)
from .new_tags_tools import get_new_tags, save_new_tags
from .file_tools import create_output_file, create_shift_output_file, create_template_log_output_file
from kaskadxml.log_utils import logger


def update_klogic_xml(klogic_xml: KlogicXML):
    new_tags = get_new_tags(klogic_xml)
    if len(new_tags):
        save_new_tags(new_tags)
        raise NewTagsError(f'Новые переменные: {len(new_tags)}')
    else:
        klogic_xml.delete_empty_groups()
        klogic_xml.delete_tags(Tag.get_bad_tags())
        klogic_xml.add_comment()
        klogic_xml.rename_tags(Tag.get_standart_tag_names())
        klogic_xml.set_noffl(Tag.get_noffl_tags())
        return create_output_file(klogic_xml), create_shift_output_file(klogic_xml)


def update_klogger_xml(klogger_xml: KloggerXML, args):
    klogger_xml.delete_old_config()
    try:
        logger.debug(klogger_xml.db_version.tag)
        klogger_xml.set_klogger_xml(args.klogic_xml.module, Tag.get_bdtp_tags())
        return create_output_file(klogger_xml)
    except AttributeError:
        raise KloggerBadFormatError('Klogger XML: Неправильный формат')


def update_alarms_xml(alarm_xml: AlarmsXML, args):
    try:
        logger.debug(alarm_xml.group_item.tag)
        alarm_xml.set_alarm_xml(args.klogic_xml.module, Tag.get_alarm_tags())
        return create_output_file(alarm_xml)
    except AttributeError:
        raise AlarmsBadFormatError('Alarm XML: Неправильный формат')

def update_mnemolist_xml(mnemolist_xml: MnemoListXML, args):
    mnemolist_xml.set_mnemolist_xml(args.klogic_xml)
    return create_output_file(mnemolist_xml)

def update_gm_mnemo_xml(gm_mnemo_xml: GM_MnemoXML, args, mnemolist_xml: MnemoListXML):
    gm_mnemo_xml.set_gm_mnemo_xml(
        args.klogic_xml,
        mnemolist_xml,
        Tag.get_kvision_alarms(),
        Tag.get_kvision_tags()
    )
    return create_output_file(gm_mnemo_xml), create_template_log_output_file(mnemolist_xml.template_log)

from kaskadxml.models import HistoryAttr, Tag
from kaskadxml.kaskad_xml import NotEnoughVar, KlogicBadFormatError
from kaskadxml.log_utils import logger


def get_new_tags(klogic_xml):
    try:
        klogic_xml.find_module()
        logger.debug(klogic_xml.module.tag)
        klogic_xml.h_remove(HistoryAttr.get_h_attrs())
        new_tags = klogic_xml.set_new_tags(Tag.get_tags_names())
        if new_tags == -1:
            raise NotEnoughVar('В группе Alarms у централи добавлены не все переменные')
        return new_tags
    except AttributeError:
        raise KlogicBadFormatError('Klogic XML: Неправильный формат')


def save_new_tags(new_tags):
    for tag in new_tags:
        new_tag = Tag(id=tag.tag_id, name=tag.tag_name, controller=tag.controller, tag_type='3')
        new_tag.save()

from kaskadxml.log_utils import logger
from dgu.models import Dgu_tag
from kaskadxml.kaskad_xml import NotEnoughVar, KlogicBadFormatError


def get_new_tags(klogic_xml):
    try:
        klogic_xml.find_module()
        logger.debug(klogic_xml.module.tag)
        new_tags = klogic_xml.set_new_tags(Dgu_tag.get_tags_names())
        return new_tags
    except AttributeError:
        raise KlogicBadFormatError('Klogic XML: Неправильный формат')


def save_new_tags(new_tags):
    for tag in new_tags:
        new_tag = Dgu_tag(id=tag.tag_id, name=tag.tag_name, controller=tag.controller, tag_type='3')
        new_tag.save()


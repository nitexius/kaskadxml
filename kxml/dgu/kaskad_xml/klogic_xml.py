import logging
from typing import Iterable, List
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from .indices import indices as i
from kaskadxml.kaskad_xml import  (
    ErrorCentralAlarm,
    NewTagAttrs,
    KlogicAttrs,
    Tag,
    get_tag_value_list,
)


def get_group_tags(tag_groups: Element) -> List[str]:
    """Получение всех переменных контроллера"""
    group_tag_names = []
    group_tag_names.append(tag_groups.attrib['Name'])
    return group_tag_names


class KlogicXML:
    """ Класс для  KlogicXML"""
    def __init__(self, xml_path, prot_code: str, gm_names: str, xml_file_name: str):
        self.xml_path = xml_path
        self.xml_file_name = xml_file_name
        self.parsed_xml = ElementTree.parse(self.xml_path)
        self.prot_code = prot_code
        self.gm_names = gm_names
        self.module = None
        self.modules = set()
        self.prot_number = 1
        self.protocols = {}
        self.new_tag_names = []
        self.new_ids = []
        self.all_new_tags_attrs = []
        self.logger = logging.getLogger(__name__)

    def get_protocol_names(self):
        return (item for item in self.gm_names.split(';'))
    
    def filter_module(self, protocol: Element):
        """Фильтр протокола с контроллерами"""
        protocols = set()
        prot_number = 1
        for gm_name in protocol.iter('Name'):
            for protocol_name in self.get_protocol_names():
                if gm_name.text == protocol_name:
                    for setting in protocol.iter('ProtCode'):
                        if setting.text == self.prot_code:
                            self.protocols[self.prot_number] = [protocol_name, protocol]
                            self.prot_number = self.prot_number + 1
                            prot_number = prot_number + 1
                            protocols.add(protocol)
        return protocols

    def find_module(self):
        """Поиск протокола с контроллерами"""
        protocols = filter(self.filter_module, self.parsed_xml.findall('.//Protocol'))
        for protocol in protocols:
            self.module = protocol[i.module]
            for module_number, module_group in enumerate(protocol):
                if module_group.tag == 'Module':
                    self.modules.add(module_group)
    
    def generate_id(self, exist_tags: Iterable) -> int:
        """Получение нового id"""
        tag_id = 1
        while any([
            tag_id in get_tag_value_list(exist_tags, 'id'),
            tag_id in self.new_ids
        ]):
            tag_id += 1
        return tag_id
    
    def check_new_tag(self, exist_tags: Iterable, tag_name: str) -> bool:
        """Проверка нового параметра"""
        return not any([
            tag_name in self.new_tag_names,
            tag_name in get_tag_value_list(exist_tags, 'name')
        ])
    
    def create_new_tag(self, exist_tags: Iterable, group: Element, tag_name: str) -> Tag:
        """Создание нового тега"""
        for setting in group.iter('KId'):
            kid = setting.text
            
        tag_attrs = NewTagAttrs(
            tag_id=self.generate_id(exist_tags),
            controller=kid,
            tag_name=tag_name
        )
        self.logger.debug('Новый параметр:')
        self.logger.debug(tag_attrs.controller)
        self.logger.debug(tag_attrs.tag_name)
        return Tag(tag_attrs)

    def update_new_lists(self, new_tag: Tag):
        """Добавление информации о новом теге в соответствующие списки"""
        self.all_new_tags_attrs.append(new_tag.tag_attr)
        self.new_tag_names.append(new_tag.tag_attr.tag_name)
        self.new_ids.append(new_tag.tag_attr.tag_id)
    
    def get_new_tags(self, exist_tags: Iterable):
        """Проверка на новые переменные"""
        for module in self.modules:
            all_inout = module.findall('.//InOut')
            for inout in all_inout:
                for tag_name in get_group_tags(inout):
                    if self.check_new_tag(exist_tags, tag_name):
                        new_tag = self.create_new_tag(exist_tags, inout[i.settings], tag_name)
                        self.update_new_lists(new_tag)

    def set_new_tags(self, exist_tags: Iterable):
        """Получение новых переменных, проверка аварий централи"""
        try:
            self.get_new_tags(exist_tags)
            return self.all_new_tags_attrs
        except ErrorCentralAlarm:
            return -1
    
    def klogic_tree_find(self) -> KlogicAttrs:
        """Получение необходимых атрибутов из klogic.xml"""
        kl_find = ()
        protocols = self.parsed_xml.findall('.//Protocol')
        for protocol in protocols:
            for setting in protocol.iter('ProtCode'):
                if setting.text == self.prot_code:
                    self.module = protocol[i.module]
                    kl_find = KlogicAttrs(
                        danfoss=protocol[i.settings][i.name],
                        protocol_name=protocol[i.settings][i.name],
                        gm=protocol[i.module][i.settings][i.name],
                        Groups=protocol[i.module],
                        fsection=self.parsed_xml.find('.//UserTask'),
                        task_name=self.parsed_xml.find('.//UserTask/Settings/Name'),
                        te=self.parsed_xml.find('.//TasksGroup0/UserTask/Settings'),
                        klogic_name=self.parsed_xml.find('.//Controller/Settings/Name'),
                        syst_num=self.parsed_xml.find('.//Controller/Settings/SystNum')
                    )
        return kl_find

    def write(self, xml_path):
        self.parsed_xml.write(xml_path)

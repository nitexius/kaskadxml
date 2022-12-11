import random
import logging
import pathlib
from dataclasses import dataclass
from typing import List
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from .klogic_xml import KlogicXML
from .indices import indices as i, constants as c
from kaskadxml.kaskad_xml import KlogicAttrs
from .alrm import stations


@dataclass
class BranchAttrs:
    name: str
    id: str
    linkid: str
    isvirtual: str
    isthispath: str
    changepath: str
    thispath: str
    permissions: str


def generate_symbols(length: int):
    """" Получение символов сегмента id """
    symbols = ''
    for i in range(length):
        symbols += random.choice(c.chars)
    return symbols


def generate_mnemo_id():
    """" Генерация id новой мнемосхемы """
    mnemo_id = ''
    for length in c.mnemo_id_length:
        mnemo_id += generate_symbols(length)
        if length != i.last_id_segment:
            mnemo_id += '-'
    return mnemo_id


def set_sub_element(branch:Element, attrs:BranchAttrs):
    ElementTree.SubElement(
        branch,
        'Branch',
        attrib={
            'Name': attrs.name,
            'id': attrs.id,
            'linkid': attrs.linkid,
            'isvirtual': attrs.isvirtual,
            'isthispath': attrs.isthispath,
            'changepath': attrs.changepath,
            'thispath': attrs.thispath,
            'permissions': attrs.permissions
        }
    )


class MnemoListXML:
    """ Класс для  MnemoListXML"""
    def __init__(self, xml_path: pathlib.Path, kl_find: KlogicAttrs, station_id: int):
        self.xml_path = xml_path
        self.parsed_xml = ElementTree.parse(self.xml_path)
        self.mnemolist_root = self.parsed_xml.getroot()
        self.xml_file_name = 'MnemoList.xml'
        self.station_id = station_id
        self.klogic_name = kl_find.klogic_name
        self.logger = logging.getLogger(__name__)
        self.module_name = ''
        self.ibp_number = ''
        self.ibp_type = ''
        self.exist_mnemo_ids = [c.null_id, ]
        self.link_group = None
        self.protocol_name = kl_find.protocol_name
        self.new_branch_id = None

    def get_station_name(self) -> str:
        """" Получение названия станции """
        station_name = ''
        for station in stations:
            if self.station_id == station[i.alrm_code]:
                station_name = station[i.alrm_text]
        return station_name
    
    def set_exist_mnemo_ids(self):
        """" Получение id существующих мнемосхем """
        branches = self.parsed_xml.findall('.//Branch')
        for branch in branches:
            self.exist_mnemo_ids.append(branch.attrib['id'].replace('{', '').replace('}', ''))

    def set_new_mnemo_id(self):
        """" Получение id новой мнемосхемы """
        new_mnemo_id = c.null_id
        while new_mnemo_id in self.exist_mnemo_ids:
            new_mnemo_id = generate_mnemo_id()
        self.exist_mnemo_ids.append(new_mnemo_id)
        return new_mnemo_id

    def set_module_atrrs(self, module: Element):
        """ Поучение информации по текущему модулю """
        self.module_name = module[i.settings][i.name].text
        self.ibp_number = self.module_name.split(' ')[i.ibp_number]
        self.ibp_type = self.module_name.split(' ')[i.ibp_type]

    def set_gm_group(self, branches: List[Element]):
        result = False
        for branch in branches:
            if branch.attrib['id'] == c.parent_group_id:
                self.new_branch_id = '{' + f'{self.set_new_mnemo_id()}' + '}'
            
                branch_attrib = BranchAttrs(
                    name=f'{self.protocol_name}',
                    id=f'{self.new_branch_id}',
                    linkid='{' + f'{c.null_id}' + '}',
                    isvirtual='false',
                    isthispath='false',
                    changepath='',
                    thispath='',
                    permissions=c.not_virtual_permissions
                )
                set_sub_element(branch, branch_attrib)
                result = True
        return result
    
    def set_module_group(self, new_branches:List[Element]):
        for new_branch in new_branches:
            if new_branch.attrib['id'] == f'{self.new_branch_id}':
            
                permissions = c.permissions1
                if self.module_name == 'ИБП 1 для ibbak':
                    permissions = c.permissions3
            
                new_branch_attrib = BranchAttrs(
                    name=f'{self.protocol_name} {self.module_name}',
                    id='{' + f'{self.set_new_mnemo_id()}' + '}',
                    linkid=c.template_id,
                    isvirtual='true',
                    isthispath='false',
                    changepath=f'KLogic\\{self.get_station_name()}\\{self.klogic_name.text}\\{self.protocol_name}\\{self.module_name}|',
                    thispath='',
                    permissions=f'{permissions}'
                )
                set_sub_element(new_branch, new_branch_attrib)
    
    def set_mnemolist_xml(self, klogic_xml: KlogicXML):
        """ Обработка MnemoListXML """
        self.set_exist_mnemo_ids()
        branches = self.parsed_xml.findall('.//Branch')
        for prot_number in range(1, klogic_xml.prot_number):
            self.protocol_name = klogic_xml.protocols[prot_number][i.protocol][i.settings][i.name].text
            if self.set_gm_group(branches):
                new_branches = self.parsed_xml.findall('.//Branch')
                modules = klogic_xml.protocols[prot_number][i.protocol].findall('.//Module')
                for module in modules:
                    self.set_module_atrrs(module)
                    self.set_module_group(new_branches)

    def write(self, xml_path):
        self.parsed_xml.write(xml_path, encoding='UTF-8')

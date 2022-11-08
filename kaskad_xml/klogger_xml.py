import pathlib
import logging
import datetime
import os
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from dataclasses import dataclass
from .klogic_xml import KlogicAttrs
from .indices import indices as i, type_names


@dataclass
class BdtpTagAttrs:
    name: str
    kid: str
    prop_list: str
    path: str


def tree_insert(parent_group: Element, insert_index: int, child_group: str, text):
    child = ElementTree.Element(child_group)
    if text:
        child.text = text
    parent_group.insert(insert_index, child)


def get_contr_name(module: Element, contr_index: int) -> str:
    """Получение названия контроллера"""
    for setting in module[contr_index][i.settings].iter('UserComment'):
        return setting.text


class KloggerXML:
    """ Класс для  KloggerXML"""

    def __init__(self, xml_path: pathlib.Path, kl_find: KlogicAttrs, station_id: int, xml_file_name: str):
        self.xml_path = xml_path
        self.xml_file_name = xml_file_name
        self.parsed_xml = ElementTree.parse(self.xml_path)
        self.db_version = self.parsed_xml.find('.//DBVersion')
        self.klogger_root = self.parsed_xml.getroot()
        self.station_id = station_id
        self.klogic_name = kl_find.klogic_name
        self.protocol_name = kl_find.protocol_name
        self.gm = kl_find.gm
        self.syst_num = kl_find.syst_num
        self.group_tags = {}
        self.all_bdtp_tags = {}
        self.bdtp_id = 1
        self.all_groups = []
        self.all_par = []
        self.cutout_flag = False
        self.checked_tag = None
        self.logger = logging.getLogger(__name__)

    def delete_old_config(self):
        """Удаление старой конфигурации klogger"""
        old_groups = self.parsed_xml.find('.//Groups')
        if isinstance(old_groups, Element):
            self.logger.debug('len(old_groups)=')
            self.logger.debug(len(old_groups))
            self.klogger_root.remove(old_groups)

    def remove_service_attrs(self, parent_group: str, group_name: str, iterables: list):
        """Удаление служебных символов в названии групп"""
        for index in reversed(iterables):
            for parent in self.parsed_xml.findall(parent_group):
                for child in parent:
                    child.tag = child.tag.replace(f'{group_name}{index}', f'{group_name}')

    def insert_grp_config(self, contr_index: int, contr: str):
        """Добавление нового контроллера в дерево конфигурации"""
        tree_insert(self.parsed_xml.find('.//Groups'), contr_index, f'Grp{contr_index}', False)
        parent_group = self.parsed_xml.find(f'.//Grp{contr_index}')
        tree_insert(parent_group, i.grp_name, 'Name', contr)
        tree_insert(parent_group, i.own_config, 'OwnCfg', 'false')
        tree_insert(parent_group, i.params, f'Params{contr_index}', False)

    def filter_bdtp_tag(self, bdtp_tag: dict) -> dict:
        """Фильтр тега с атрибутом БДТП"""
        if self.checked_tag.attrib['Name'] == bdtp_tag['name']:
            return bdtp_tag

    def check_cutout(self, bdtp_tag: dict):
        """Проверка добавлена ли уже уставка"""
        return (True
                if not all([bdtp_tag['alarm_id'] == 'Cutout', self.cutout_flag]) else False
                )

    def set_cutout_flag(self, bdtp_tag: dict):
        if bdtp_tag['alarm_id'] == 'Cutout':
            self.cutout_flag = True

    def get_tag_name(self):
        """Получение имени тега"""
        return self.checked_tag.attrib['Name']

    def get_kid(self) -> str:
        """Получение адреса тега из klogic.xml"""
        for setting in self.checked_tag[i.settings].iter('KId'):
            return setting.text

    def get_prop_list(self) -> str:
        """Получение типа тега"""
        for setting in self.checked_tag[i.settings].iter('PropList'):
            return setting.attrib['TagType']

    def set_bdtp_tag(self, module: Element, contr_index: int) -> BdtpTagAttrs:
        """Получение атрибутов архивируемого тега"""
        return BdtpTagAttrs(
            name=self.get_tag_name(),
            kid=self.get_kid(),
            prop_list=self.get_prop_list(),
            path=f'{self.klogic_name.text}.{self.protocol_name.text}.{self.gm.text}.{get_contr_name(module, contr_index)}.{self.get_tag_name()}'
        )

    def set_group_tags(self, module: Element, contr_index: int, tag_number: int):
        """Получение атрибутов всех архивируемых тегов контроллера"""
        self.group_tags[tag_number] = self.set_bdtp_tag(module, contr_index)

    def get_bdtp_tags(self, module: Element, bdtp_tags: Iterable):
        """Получение всех архивируемых параметров, с разделением по контроллерам"""
        for contr_index in range(len(module))[i.first_contr:]:
            tag_number = 0
            self.group_tags = {}
            self.cutout_flag = False
            self.all_groups.append(contr_index)
            self.insert_grp_config(contr_index, get_contr_name(module, contr_index))
            self.logger.debug(get_contr_name(module, contr_index))

            for self.checked_tag in module[contr_index][i.first_tag:]:
                for bdtp_tag in filter(self.filter_bdtp_tag, bdtp_tags):
                    if self.check_cutout(bdtp_tag):
                        self.logger.debug(bdtp_tag)
                        self.set_group_tags(module, contr_index, tag_number)
                        self.set_cutout_flag(bdtp_tag)
                        tag_number += 1
            self.all_bdtp_tags[contr_index] = self.group_tags

    def set_valtype(self, grp_index: int, par_index: int) -> str:
        return (
            '2'
            if self.all_bdtp_tags[grp_index][par_index].prop_list == 'B' else '1'
        )

    def set_typename(self, grp_index: int, par_index: int) -> str:
        return type_names.get(self.all_bdtp_tags[grp_index][par_index].prop_list)

    def set_klogger_xml(self, module: Element, bdtp_tags: Iterable) -> str:
        """Формирование klogger.xml"""
        tree_insert(self.klogger_root, i.groups_index, 'Groups', False)
        self.get_bdtp_tags(module, bdtp_tags)

        for grp in self.all_groups:
            for par in range(len(self.all_bdtp_tags[grp])):
                self.all_par.append(par)
                tree_insert(self.parsed_xml.find(f'.//Params{grp}'), par, f'Par{par}', False)
                parent_group = self.parsed_xml.find(f'.//Params{grp}/Par{par}')
                tree_insert(parent_group, i.zone, 'Zone', f'{self.klogic_name.text}')
                tree_insert(parent_group, i.parid, 'ParID', f'{self.bdtp_id}')
                tree_insert(parent_group, i.stid, 'StId', f'{self.station_id}')
                tree_insert(parent_group, i.type, 'Type', '222')
                tree_insert(parent_group, i.grid, 'GrId', f'{self.syst_num.text}')
                tree_insert(parent_group, i.psid, 'PsId', self.all_bdtp_tags[grp][par].kid)
                tree_insert(parent_group, i.valtype, 'ValType', self.set_valtype(grp, par))
                tree_insert(parent_group, i.typename, 'TypeName', self.set_typename(grp, par))
                tree_insert(parent_group, i.cipher, 'Cipher', str(self.all_bdtp_tags[grp][par].name))
                tree_insert(parent_group, i.klogger_name, 'Name', self.all_bdtp_tags[grp][par].path)
                tree_insert(parent_group, i.usepreagr, 'UsePreAgr', 'false')
                self.bdtp_id += 1

        self.remove_service_attrs('.//Groups', 'Grp', self.all_groups)
        self.remove_service_attrs('.//Groups/Grp', 'Params', self.all_groups)
        self.remove_service_attrs('.//Groups/Grp/Params', 'Par', self.all_par)

        return "Klogger XML: Обработка завершена"

    def write(self, xml_path):
        self.parsed_xml.write(xml_path, encoding='UTF-8')

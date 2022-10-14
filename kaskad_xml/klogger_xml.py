import pathlib
from typing import Iterable
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from dataclasses import dataclass
from .klogic_indexes import FIRST_CONTR_INDEX, FIRST_TAG_INDEX, SETTINGS_INDEX
from .klogger_indexes import (GROUPS_INDEX, GRP_NAME_INDEX, OWNCFG_INDEX, PARAMS_INDEX, ZONE_INDEX, PARID_INDEX,
                             STID_INDEX, TYPE_INDEX, GRID_INDEX, PSID_INDEX, VALTYPE_INDEX, TYPENAME_INDEX,
                             CIPHER_INDEX, KLOGGER_NAME_INDEX, USEPREAGR_INDEX)


@dataclass
class KlogicAttrs:
    danfoss: Element
    protocol_name: Element
    gm: Element
    Groups: Element
    fsection: Element
    task_name: Element
    te: Element
    klogic_name: Element
    syst_num: Element


def tree_insert(parent_group: Element, insert_index: int, child_group: str, text):
    child = ElementTree.Element(child_group)
    if text:
        child.text = text
    parent_group.insert(insert_index, child)


class KloggerXML:
    """ Класс для  KloggerXML"""

    def __init__(self, xml_path: pathlib.Path, kl_find: KlogicAttrs, station_id: int):
        self.xml_path = xml_path
        self.parsed_xml = ElementTree.parse(self.xml_path)
        self.db_version = self.parsed_xml.find('.//DBVersion')
        self.klogger_root = self.parsed_xml.getroot()
        self.station_id = station_id
        self.klogic_name = kl_find.klogic_name
        self.protocol_name = kl_find.protocol_name
        self.gm = kl_find.gm
        self.syst_num = kl_find.syst_num
        self.all_bdtp_tags = {}
        self.bdtp_id = 1
        self.all_groups = []
        self.all_par = set()

    def delete_old_config(self):
        """Удаление старой конфигурации klogger"""
        try:
            old_groups = self.parsed_xml.find('.//Groups')
            print('len(old_groups)=', len(old_groups))
            if len(old_groups):
                self.klogger_root.remove(old_groups)
        except TypeError:
            print('Конфигурация БДТП пуста')
            pass

    def remove_service_attrs(self, parent_group: str, group_name: str, iterables: Iterable):
        """Удаление служебных символов в названии групп"""
        for index in iterables:
            for parent in self.parsed_xml.findall(parent_group):
                for child in parent:
                    child.tag = child.tag.replace(f'{group_name}{index}', f'{group_name}')

    def insert_grp_config(self, contr_index: int, contr: str):
        """Добавление нового контроллера в дерево конфигурации"""
        tree_insert(self.parsed_xml.find('.//Groups'), contr_index, f'Grp{contr_index}', False)
        parent_group = self.parsed_xml.find(f'.//Grp{contr_index}')
        tree_insert(parent_group, GRP_NAME_INDEX, 'Name', contr)
        tree_insert(parent_group, OWNCFG_INDEX, 'OwnCfg', 'false')
        tree_insert(parent_group, PARAMS_INDEX, f'Params{contr_index}', False)

    def get_bdtp_tags(self, module: Element, bdtp_tags: Iterable):
        """Получение всех архивируемых параметров, с разделением по контроллерам"""
        for contr_index in range(len(module))[FIRST_CONTR_INDEX:]:
            self.all_groups.append(contr_index)
            contr = module[contr_index].attrib['Name']
            self.insert_grp_config(contr_index, contr)
            tag_number = 0
            group_tags = {}
            for inout in module[contr_index][FIRST_TAG_INDEX:]:
                for bdtp_tag in bdtp_tags:
                    tag = {}
                    if inout.attrib['Name'] == bdtp_tag['name']:
                        tag_name = inout.attrib['Name']
                        tag['Name'] = tag_name
                        for setting in inout[SETTINGS_INDEX].iter('KId'):
                            tag['KId'] = setting.text
                        for setting in inout[SETTINGS_INDEX].iter('PropList'):
                            tag['PropList'] = setting.attrib['TagType']
                        tag['st'] = f'{self.klogic_name.text}.{self.protocol_name.text}.{self.gm.text}.{contr}.{tag_name}'
                        group_tags[tag_number] = tag
                        tag_number += 1
            self.all_bdtp_tags[contr_index] = group_tags

    def get_valtype(self, grp_index: int, par_index: int) -> str:
        return (
            '2'
            if self.all_bdtp_tags[grp_index][par_index]['PropList'] == 'B' else '1'
        )

    def get_typename(self, grp_index: int, par_index: int) -> str:
        type_name = ''
        if self.all_bdtp_tags[grp_index][par_index]['PropList'] == 'B':
            type_name = 'Дискретный вход (Логический)'
        if self.all_bdtp_tags[grp_index][par_index]['PropList'] == 'F':
            type_name = 'Аналоговый вход (Вещественный)'
        if self.all_bdtp_tags[grp_index][par_index]['PropList'] == 'W':
            type_name = 'Аналоговый выход (Целочисленный)'
        return type_name

    def bdtp(self, module: Element, bdtp_tags: Iterable) -> str:
        """Формирование klogger.xml"""
        tree_insert(self.klogger_root, GROUPS_INDEX, 'Groups', False)
        self.get_bdtp_tags(module, bdtp_tags)

        for grp in self.all_groups:
            for par in range(len(self.all_bdtp_tags[grp])):
                self.all_par.add(par)
                tree_insert(self.parsed_xml.find(f'.//Params{grp}'), par, f'Par{par}', False)
                parent_group = self.parsed_xml.find(f'.//Params{grp}/Par{par}')
                tree_insert(parent_group, ZONE_INDEX, 'Zone', f'{self.klogic_name.text}')
                tree_insert(parent_group, PARID_INDEX, 'ParID', f'{self.bdtp_id}')
                tree_insert(parent_group, STID_INDEX, 'StId', f'{self.station_id}')
                tree_insert(parent_group, TYPE_INDEX, 'Type', '222')
                tree_insert(parent_group, GRID_INDEX, 'GrId', f'{self.syst_num.text}')
                tree_insert(parent_group, PSID_INDEX, 'PsId', self.all_bdtp_tags[grp][par]['KId'])
                tree_insert(parent_group, VALTYPE_INDEX, 'ValType', self.get_valtype(grp, par))
                tree_insert(parent_group, TYPENAME_INDEX, 'TypeName', self.get_valtype(grp, par))
                tree_insert(parent_group, CIPHER_INDEX, 'Cipher', str(self.all_bdtp_tags[grp][par]['Name']))
                tree_insert(parent_group, KLOGGER_NAME_INDEX, 'Name', self.all_bdtp_tags[grp][par]['st'])
                tree_insert(parent_group, USEPREAGR_INDEX, 'UsePreAgr', 'false')
                self.bdtp_id += 1

        self.remove_service_attrs('.//Groups', 'Grp', self.all_groups)
        self.remove_service_attrs('.//Groups/Grp', 'Params', self.all_groups)
        self.remove_service_attrs('.//Groups/Grp/Params', 'Par', self.all_par)

        return "Klogger XML: Обработка завершена"

    def write(self, xml_path: pathlib.Path):
        if xml_path == '':
            xml_path = self.xml_path
        print(xml_path)
        self.parsed_xml.write(xml_path, encoding='UTF-8')

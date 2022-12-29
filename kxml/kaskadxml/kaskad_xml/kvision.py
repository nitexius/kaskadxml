import random
import logging
import pathlib
import os.path
from io import BytesIO
from dataclasses import dataclass
from typing import List, Iterable
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from .klogic_xml import KlogicXML
from .indices import (
    indices as i,
    constants as c,
    template_id_attrs,
    constants_map as constants,
    xo_types,
    info_properties as info_prop,
    freon_control as f_ctrl,
    freon_properties as f_prop,
    refrigerator_control as ref_ctrl,
    refrigerator_properties as ref_prop
)
from kaskadxml.kaskad_xml import KlogicAttrs
from .alrm import stations
from .template_tags import template_tags
from kxml.settings import MEDIA_ROOT
from .alarms_xml import get_central_tags, get_child_group


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
    

@dataclass
class TemplateAttrs:
    contr_name: str
    tags: List[str]
    template_name: str
    no_template: bool
    link_error: bool


@dataclass
class IdCharAttrs:
    virtual_branch_id_char: int
    template_mnemo_id_char: int


@dataclass
class TagAttrs:
    type: str
    checked: str


def get_input_file(file) -> BytesIO:
    """ Получение исходного файла в виде BytesIO """
    input_file = BytesIO(file)
    input_file.seek(0)
    return input_file


def generate_symbols(length: int) -> str:
    """" Получение символов сегмента id """
    symbols = ''
    for i in range(length):
        symbols += random.choice(c.chars)
    return symbols


def generate_mnemo_id() -> str:
    """" Генерация id новой мнемосхемы """
    mnemo_id = ''
    for length in c.mnemo_id_length:
        mnemo_id += generate_symbols(length)
        if length != i.last_id_segment:
            mnemo_id += '-'
    return mnemo_id


def set_new_branch(branch:Element, attrs:BranchAttrs):
    """" Добавление виртуальной мнемосхемы в xml """
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


def get_id_segments(mnemo_id: str) -> List[str]:
    """" Получение сегментов id мнемосхемы """
    segments = []
    for s in range(0, 5):
        segments.append(mnemo_id.replace('{', '').replace('}', '').split('-')[s])
    return segments


def check_id_segments(segments: List[str]) -> bool:
    """" Проверка длинны полученного сегмента id """
    for segment_number, segment  in enumerate(segments):
        if len(segment) < c.id_segmets[segment_number]:
            return True


def set_template_mnemo(group_tags: Iterable):
    """" Получение шаблона мнемосхемы """
    result = (False, None)
    for attrs in template_id_attrs:
        res_include = [tag for tag in attrs.include_tags if tag in group_tags]
        res_exclude = [tag for tag in attrs.exclude_tags if tag not in group_tags]
        if all([
            res_include == attrs.include_tags,
            res_exclude == attrs.exclude_tags
        ]):
            result = (constants.get(attrs.template_id), attrs.template_name)
            break
    return result


def get_group_tags(group: Element) -> List[str]:
    """" Получение переменных контроллера """
    group_tags = []
    for inout in group[i.first_tag:]:
        group_tags.append(inout.attrib['Name'])
    return group_tags


def get_group_comment(group: Element) -> str:
    """" Получение комментария контроллера """
    for group_setting in group[i.settings].iter('UserComment'):
        return group_setting.text


def get_station_name(station_id: int) -> str:
    """" Получение названия станции """
    station_name = ''
    for station in stations:
        if station_id == station[i.alrm_code]:
            station_name = station[i.alrm_text]
    return station_name


def set_new_id(exist_ids: List) -> str:
    """ Генерация id """
    new_id = c.null_id
    while new_id in exist_ids:
        new_id = generate_mnemo_id()
    exist_ids.append(new_id)
    return new_id


class MnemoListXML:
    """ Класс для MnemoListXML"""
    def __init__(self, xml_path: pathlib.Path, kl_find: KlogicAttrs, station_id: int):
        self.xml_path = xml_path
        self.parsed_xml = ElementTree.parse(self.xml_path)
        self.mnemolist_root = self.parsed_xml.getroot()
        self.xml_file_name = 'MnemoList.xml'
        self.gms_branch = self.get_gms_branch()
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
        self.template_log = []
        self.char_group = None
        self.gm_mnemo_id = None
        self.gm_mnemo = None
        self.template_tags = None

    def set_gm_char(self, klogic_xml: KlogicXML) -> str:
        """" Получение первой буквы названия ГМ """
        for name_group in klogic_xml.module[i.settings].iter('Name'):
            self.module_name = name_group.text
            return name_group.text[i.first_char]
    
    def get_gms_branch(self) -> Element:
        """" Получение группы ГМ """
        branches = self.parsed_xml.findall('.//Branch')
        for branch in branches:
            if branch.attrib['id'] == c.gm_group_id:
                return branch

    def filter_template_tags(self, group_tag: str) -> str:
        """ Фильтр переменных, отсутствующих в шаблоне """
        if group_tag not in self.template_tags:
            return group_tag

    def check_template_tags(self, group_tags: Iterable, contr_model: str) -> List[str]:
        """" Получение переменных, отсутствующих в шаблоне """
        not_matched_tags = []
        self.template_tags = template_tags[contr_model]
        tags = filter(self.filter_template_tags, group_tags)
        for tag in tags:
            not_matched_tags.append(tag)
        return not_matched_tags
    
    def get_template_mnemo_id(self, group: Element) -> str:
        """" Получение id шаблона мнемосхемы """
        template_attrs = TemplateAttrs(
            contr_name=group[i.settings][i.name].text,
            tags=[],
            template_name='',
            no_template=False,
            link_error=False
        )

        group_tags = get_group_tags(group)

        template_id, template_name = set_template_mnemo(group_tags)
        if template_id:
            template_attrs.tags = self.check_template_tags(group_tags, template_name)
            template_attrs.template_name = template_name
        else:
            template_attrs.no_template = True
            
        self.template_log.append(template_attrs)
        return template_id

    def set_exist_mnemo_ids(self):
        """" Получение id существующих мнемосхем """
        branches = self.parsed_xml.findall('.//Branch')
        for branch in branches:
            self.exist_mnemo_ids.append(branch.attrib['id'].replace('{', '').replace('}', ''))

    def find_char_group(self, gm_char: str) -> Element:
        """" Получение группы с первой буквой ГМ """
        for char_group in self.gms_branch:
            if char_group.attrib['Name'] == gm_char:
                return char_group
    
    def filter_gm_group(self, gm_group: Element) -> Element:
        """" Фильтр группы ГМ """
        if gm_group.attrib['Name'] == f'{self.module_name}':
            return gm_group
    
    def remove_old_gm_group(self, char_group: Element):
        """" Удаление старой группы с мнемосхемами ГМ """
        gm_groups = char_group.findall('.//Branch')
        groups = filter(self.filter_gm_group, gm_groups)
        for gm_group in groups:
            char_group.remove(gm_group)
    
    def set_gm_group(self, gm_char: str):
        """" Добавление группы ГМ """
        char_group = self.find_char_group(gm_char)
        self.remove_old_gm_group(char_group)
        self.new_branch_id = '{' + f'{set_new_id(self.exist_mnemo_ids)}' + '}'
        
        branch_attrib = BranchAttrs(
            name=f'{self.module_name}',
            id=f'{self.new_branch_id}',
            linkid='{' + f'{c.null_id}' + '}',
            isvirtual='false',
            isthispath='false',
            changepath='',
            thispath='',
            permissions=c.not_virtual_permissions
        )
        set_new_branch(char_group, branch_attrib)
    
    def get_new_branch(self) -> Element:
        """" Получение созданной группы ГМ """
        new_branches = self.parsed_xml.findall('.//Branch')
        for new_branch in new_branches:
            if new_branch.attrib['id'] == self.new_branch_id:
                return new_branch
    
    def set_gm_mnemo(self, gm_branch: Element, gm_code: str):
        """" Добавление новой мнемосхемы ГМ в Mnemolist """
        self.gm_mnemo_id = f'{set_new_id(self.exist_mnemo_ids)}'
        ElementTree.SubElement(gm_branch, 'Mnemo', attrib={'ID': self.gm_mnemo_id})
        mnemos = gm_branch.findall('.//Mnemo')
        for mnemo in mnemos:
            if mnemo.attrib['ID'] == self.gm_mnemo_id:
                self.gm_mnemo = mnemo
                self.gm_mnemo.insert(0, get_child_group('Name', f'{gm_code} Прилавки и камеры'))
                self.gm_mnemo.insert(1, get_child_group('Comments', False))
                self.gm_mnemo.insert(2, get_child_group('Engineering', 'false'))
                self.gm_mnemo.insert(3, get_child_group('PopUp', 'true'))
                self.gm_mnemo.insert(4, get_child_group('AutoLoad', 'false'))
                self.gm_mnemo.insert(5, get_child_group('AutoView', 'false'))
                self.gm_mnemo.insert(6, get_child_group('Permissions', '11'))
                self.gm_mnemo.insert(7, get_child_group('DockPopup', 'false'))
                self.gm_mnemo.insert(8, get_child_group('WhereDockPopup', '0'))
                self.gm_mnemo.insert(9, get_child_group('ParamList', False))
    
    def set_virtual_mnemo(self, new_branch: Element, template_id: str, group_name: str, group_comment: str, gm: str):
        """" Создание виртуальной мнемосхемы """
        if group_comment:
            address = group_comment.split('..')[i.address]
        new_branch_attrib = BranchAttrs(
            name=f'{address}-{gm}',
            id='{' + f'{set_new_id(self.exist_mnemo_ids)}' + '}',
            linkid=template_id,
            isvirtual='true',
            isthispath='false',
            changepath=f'KLogic\\{get_station_name(self.station_id)}\\{self.klogic_name.text}\\{self.protocol_name.text}\\{self.module_name}\\{group_name}|',
            thispath='',
            permissions=f'{c.permissions1}'
        )
        set_new_branch(new_branch, new_branch_attrib)

    def set_mnemolist_xml(self, klogic_xml: KlogicXML):
        """ Обработка MnemoListXML """
        self.set_exist_mnemo_ids()
        gm_code = str(klogic_xml.klogic_tree_find().gm.text).split('(')[1].replace(')', '')
        groups = klogic_xml.module.findall('.//Group')
        self.set_gm_group(self.set_gm_char(klogic_xml))
        new_branch = self.get_new_branch()
        
        for group in groups:
            template_id = self.get_template_mnemo_id(group)
            if template_id:
                if group.attrib['Name'] != 'Alarms':
                    self.set_virtual_mnemo(
                        new_branch,
                        template_id,
                        group.attrib['Name'],
                        get_group_comment(group),
                        gm_code
                    )

        self.set_gm_mnemo(new_branch, gm_code)

    def write(self, xml_path):
        self.parsed_xml.write(xml_path, encoding='UTF-8')


def get_mnemolist_branch(branches: List[Element], mnemolist_xml: MnemoListXML) -> Element:
    """" Получение группы виртуальных мнемосхем ГМ """
    for branch in branches:
        if branch.attrib['Name'] == mnemolist_xml.module_name:
            return branch


def get_refr_tag_id(passp: Element) -> int:
    """" Получение адреса тега, привязанного к холодильнику """
    tag_id = ''
    for attr in passp.iter('Name'):
        for l in c.refr_id_seq:
            tag_id += attr.text[l]
    return int(tag_id, 16)


def template_char_replace(chars: str):
    """" Замена символа id группы шаблона """
    return [char for char in range(1, c.chars_id_len) if chars in c.chars_id[char]]


def find_refr_tag(passp:Element, group:Element) -> bool:
    """" Поиск тега """
    for inout in group:
        for inout_setting in inout[i.settings].iter('KId'):
            if inout_setting.text == str(get_refr_tag_id(passp)):
                return True


def get_kontr_address(group:Element) -> str:
    """" Получение адреса контроллера """
    for group_setting in group[i.settings].iter('UserComment'):
        return group_setting.text.split('..')[i.address]


def find_link_mnemo_id(gm_child_branch: Element, branches: List[Element], virtual_mnemo_name: str) -> str:
    """" Получение id мнемосхемы шаблона """
    if gm_child_branch.attrib['Name'] == virtual_mnemo_name:
        for branch in branches:
            if branch.attrib['id'] == gm_child_branch.attrib['linkid']:
                for mnemo in branch.iter('Mnemo'):
                    return mnemo.attrib['ID']


def check_central(element: Element, central_tags: list) -> bool:
    """Определение контроллера, как контроллер централи"""
    result = False
    for in_out in element[i.first_tag:]:
        for central_tag in central_tags:
            if in_out.attrib['Name'] == central_tag['name']:
                result = True
    return result


def set_template_xml_path():
    """" Получение шаблона мнемосхемы ГМ """
    with open(os.path.join(MEDIA_ROOT, 'mnemo_template.xml'), 'rb') as mnemo_template_xml:
        return get_input_file(mnemo_template_xml.read())


def get_module_name(klogic_xml: KlogicXML) -> str:
    """" Полечения названия модуля в Klogic """
    for name_group in klogic_xml.module[i.settings].iter('Name'):
        return name_group.text


def set_param_list_group(gm_mnemo: Element) -> Element:
    """" Получение группы ParamList """
    for group in gm_mnemo:
        if group.tag == 'ParamList':
            return group


def set_refr_type(contr_name: str) -> str:
    """" Определение типа холодильника """
    refr_type = 'rtMiddleTemCentral'
    xo_type = contr_name.split('_')[i.xo_type]
    if xo_type in xo_types.nt:
        refr_type = 'rtLowTemCentral'
    if any([
        xo_type in xo_types.ceh,
        xo_type in xo_types.server,
        xo_type in xo_types.central_room
    ]):
        refr_type = 'rtVPO'
    return refr_type


def set_alarm_tag_attrs(tag: dict) -> TagAttrs:
    """" Получение атрибутов аварий для визуализации """
    return (
        TagAttrs(type='0', checked='true')
        if tag['alarm_id'] != 'A45' else TagAttrs(type='11', checked='true')
    )


def get_klogic_addr(inout: Element) -> str:
    """" Получение адреса контроллера (klogic-svc) """
    for setting in inout[i.settings].iter('KId'):
        return setting.text


def set_hex_chars(integer: int, length: int) -> str:
    """" Получение заглавных символов в 16-системе """
    hex_chars = str(hex(integer)[i.hex_char:].upper())
    if length:
        while len(hex_chars) < length:
            hex_chars = '0' + hex_chars
    return hex_chars


def set_refr_child_group(parent_group: Element, ref_elem_attrs: dict, text_map: dict, max_index: int, sequence: List):
    """ Добавление необходимых групп в холодильник """
    for group_index in range(0, max_index):
        if group_index in sequence:
            ctrl_text = text_map.get(ref_ctrl[group_index].name)
        else:
            ctrl_text = ref_elem_attrs[group_index].text
    
        parent_group.insert(
            group_index,
            get_child_group(
                ref_elem_attrs[group_index].name,
                ctrl_text
            )
        )


def set_refr_control_xml(control_group: Element, xml_id: str) -> Element:
    """ Добавление группы Control XML в холодильник """
    control_xml = control_group[i.control_xml]
    control_xml.insert(0, get_child_group('Mnemo', '{' + f'{xml_id}' + '}'))
    control_xml.insert(1, get_child_group('Passps', False))
    return control_xml[i.passps]


class GM_MnemoXML:
    """ Класс для Мнемосхемы ГМ XML """
    def __init__(self, station_id: int):
        self.xml_file_name = None
        self.template_xml_path = set_template_xml_path()
        self.parsed_template_xml = ElementTree.parse(self.template_xml_path)
        self.template_xml_root = self.parsed_template_xml.getroot()
        self.template_controls = self.parsed_template_xml.find('.//Controls')
        self.exist_control_ids = [c.null_id, ]
        self.station_id = station_id
        self.logger = logging.getLogger(__name__)
        self.virtual_id = None
        self.virtual_branch_id_char = ''
        self.template_mnemo_id_char = ''
        self.left_coord = 100
        self.top_coord = 50
        self.inout_name = None
        self.cutout_flag = False
        self.svc_path = None
        self.group_number = None

    def set_refr_tag_addr(self, inout: Element):
        """" Преобразование адреса тега для холодильника """
        kid_text = get_klogic_addr(inout)
        self.logger.debug(kid_text)
        kid = set_hex_chars(int(kid_text), length=4)
        tag_id = ''
    
        for l in c.refr_tag_addr_seq:
            tag_id += kid[l]
        self.logger.debug(f'{kid}, {tag_id}')
        return kid, tag_id

    def set_svc_path(self, klogic_xml: KlogicXML) -> str:
        """" Получение пути к klogic-svc """
        station_hex = set_hex_chars(int(self.station_id), length=2)
        klogic_addr_hex = set_hex_chars(int(klogic_xml.klogic_tree_find().syst_num.text), length=2)
        return f'${station_hex}$DE${klogic_addr_hex}$'
    
    def set_new_control(self, group_attr: str, class_id: str):
        """" Добавление нового элемента на мнемосхему """
        ElementTree.SubElement(
            self.template_controls,
            f'Control--{group_attr}',
            attrib={'ClassID': class_id, },
        )
    
    def char_id_plus(self, args: IdCharAttrs):
        """" Сложение символов id шаблона и id группы виртуальной мнемосхемы"""
        self.virtual_id += set_hex_chars(args.virtual_branch_id_char + args.template_mnemo_id_char, False)
    
    def char_id_minus(self, args: IdCharAttrs):
        """" Вычитание символов id шаблона и id группы виртуальной мнемосхемы"""
        self.virtual_id += set_hex_chars(args.virtual_branch_id_char - args.template_mnemo_id_char, False)

    def set_template_char(self, chars: str):
        """" Получение символа id для группы шаблона """
        templ_char_replace = template_char_replace(chars)
        return (
            templ_char_replace[i.templ_char]
            if templ_char_replace else int(self.template_mnemo_id_char, 16)
        )

    def set_id_segment(self, segment_number: int, segment: str, templ_segments: List[str], virtual_segments: List[str]):
        """" Генерация сегмента id виртуальной мнемосхемы """
        for char_number, char in enumerate(segment):
            self.virtual_branch_id_char = virtual_segments[segment_number][char_number]
            self.template_mnemo_id_char = templ_segments[segment_number][char_number]
        
            args = IdCharAttrs(
                virtual_branch_id_char=int(self.virtual_branch_id_char, 16),
                template_mnemo_id_char=self.set_template_char(
                    f'{self.template_mnemo_id_char}{self.virtual_branch_id_char}'
                )
            )
        
            if f'{self.template_mnemo_id_char}{self.virtual_branch_id_char}' in c.t_plus:
                self.char_id_plus(args)
            else:
                self.char_id_minus(args)
    
    def set_virtual_mnemo_id(self, templ_segments: List[str], virtual_segments: List[str]):
        """" Генерация id виртуальной мнемосхемы """
        for segment_number, segment in enumerate(templ_segments):
            if segment_number > i.segm_2:
                self.virtual_id += f'{templ_segments[i.segm_3]}-{templ_segments[i.segm_4]}{c.brace_r}'
                break
            else:
                self.set_id_segment(segment_number, segment, templ_segments, virtual_segments)
            self.virtual_id += '-'
    
    def set_refr_mnemo_link(self, control: Element, group: Element, mnemolist_xml: MnemoListXML):
        """" Привязка виртуальной мнемосхемы к холодильнику """
        for mnemo in control.iter('Mnemo'):
            if any([
                'X' in self.virtual_id,
                check_id_segments(get_id_segments(self.virtual_id))
            ]):
                self.controls.remove(control)
                new_log_str = TemplateAttrs(
                    contr_name=group.attrib['Name'],
                    tags=[],
                    template_name='',
                    no_template=False,
                    link_error=True
                )
                mnemolist_xml.template_log.append(new_log_str)
            else:
                mnemo.text = self.virtual_id

    def set_param_info_element(self, kid: str):
        """" Добавление элемента Информация о параметре на мнемосхему ГМ """
        self.set_new_control(f'i{self.group_number}', c.info_class_id)
        
        control_group = self.template_controls.find(f'.//Control--i{self.group_number}')
        control_group.insert(0, get_child_group('ID', '{' + f'{set_new_id(self.exist_control_ids)}' + '}'))
        control_group.insert(1, get_child_group('Left', str(self.left_coord)))
        control_group.insert(2, get_child_group('Top', str(self.top_coord - c.shift_coord)))
        control_group.insert(3, get_child_group('Width', '100'))
        control_group.insert(4, get_child_group('Height', '16'))
        control_group.insert(5, get_child_group('Name', f'Информация о параметре {self.group_number}'))
        control_group.insert(6, get_child_group('Properties', False))
        properties = control_group[i.properties]
        properties.insert(0, get_child_group('PasspHead', f'{self.svc_path}{kid}'))
        
        for prop_index in range(1, 16):
            properties.insert(
                prop_index,
                get_child_group(
                    info_prop[prop_index].name,
                    info_prop[prop_index].text
                )
            )

    def set_freon_warning(self):
        """" Добавление элемента с текстом о датчике утечки фреона на мнемосхему ГМ """
        self.set_new_control('freon', c.str_text_class_id)
        
        control_group = self.template_controls.find('.//Control--freon')
        control_group.insert(0, get_child_group('ID', '{' + f'{set_new_id(self.exist_control_ids)}' + '}'))

        for cont_index in range(1,7):
            control_group.insert(
                cont_index,
                get_child_group(
                    f_ctrl[cont_index].name,
                    f_ctrl[cont_index].text
                )
            )
        
        properties = control_group[i.properties]
        for prop_index in range(0,13):
            properties.insert(
                prop_index,
                get_child_group(
                    f_prop[prop_index].name,
                    f_prop[prop_index].text
                )
            )
    
    def set_mnemo_links(self, klogic_xml: KlogicXML, mnemolist_xml: MnemoListXML):
        """" Привязка виртуальных мнемосхем к холодильникам """
        gm = str(klogic_xml.klogic_tree_find().gm.text).split('(')[i.gm_code].replace(')', '')
        groups = klogic_xml.module.findall('.//Group')
        branches = mnemolist_xml.parsed_xml.findall('.//Branch')
        for control in self.template_controls:
            try:
                if control.attrib['ClassID'] == c.refr_class_id:
                    passp = control.find('.//Passps')[i.first_passp]
                    for group in groups:
                        if find_refr_tag(passp, group):
                            self.logger.debug(f'{group.attrib}, {control[i.control_name].text}')
                            for virtual_branch in get_mnemolist_branch(branches, mnemolist_xml):
                                template_mnemo_id = find_link_mnemo_id(
                                    virtual_branch,
                                    branches,
                                    f'{get_kontr_address(group)}-{gm}'
                                )
                                if template_mnemo_id:
                                    self.virtual_id = '{'
                                    template_mnemo_id_segments = get_id_segments(template_mnemo_id)
                                    virtual_branch_id_segments = get_id_segments(virtual_branch.attrib['id'])
                                    self.logger.debug(template_mnemo_id_segments)
                                    self.logger.debug(virtual_branch_id_segments)
                                
                                    self.set_virtual_mnemo_id(template_mnemo_id_segments, virtual_branch_id_segments)
                                    self.set_refr_mnemo_link(control, group, mnemolist_xml)

                                    self.logger.debug(self.virtual_id)
                                    self.logger.debug('///////////////////////')
        
            except KeyError:
                continue
    
    def set_gm_mnemo_name(self, gm: str):
        """" Переименование мнемосхемы ГМ """
        for name_group in self.template_xml_root.iter('Name'):
            name_group.text = name_group.text.replace('999999', f'{gm}')
    
    def find_iec_protocol(self, klogic_xml: KlogicXML):
        """" Проверка на наличие протокола с датчиком утечки фреона """
        if klogic_xml.iec_prot_detected:
            self.set_freon_warning()
    
    def set_coordinates(self):
        """" Получение координат элемента визуализации """
        self.left_coord = self.left_coord + c.width + c.shift
        if self.left_coord > c.max_left_coord:
            self.left_coord = c.default_left_coord
            self.top_coord = self.top_coord + c.height + c.shift
            
    def filter_tags(self, tag: dict) -> dict:
        """" Фильтр переменной """
        if self.inout_name == tag['name']:
            return tag

    def check_cutout(self, tag: dict) -> bool:
        """" Проверка на повторное добавление уставки в холодильник """
        return (
            True
            if tag['kvision_attr'] == 'cutout' and self.cutout_flag else False
        )

    def set_kvision_tag_attrs(self, tag: dict) -> TagAttrs:
        """" Получение атрибутов не аварийных переменных для визуализации """
        tag_attrs_map = {
            'u59': TagAttrs(type='3', checked='false'),
            'u58': TagAttrs(type='4', checked='false'),
            'u60': TagAttrs(type='5', checked='false'),
            'u61': TagAttrs(type='7', checked='true'),
            'u17': TagAttrs(type='1', checked='true'),
            'cutout': TagAttrs(type='2', checked='true'),
            'ekc_state': TagAttrs(type='6', checked='true')
        }
        
        if tag['kvision_attr'] == 'cutout':
            self.cutout_flag = True
        return TagAttrs(
            type=tag_attrs_map.get(tag['kvision_attr']).type,
            checked=tag_attrs_map.get(tag['kvision_attr']).checked
        )
    
    def set_tag_path(self, klogic_xml: KlogicXML, contr_name: str) -> str:
        """ Получение пути к тегу """
        kl_find = klogic_xml.klogic_tree_find()
        module_name = get_module_name(klogic_xml)
        return f'KLogic\\{get_station_name(self.station_id)}\\{kl_find.klogic_name.text}\\{kl_find.protocol_name.text}\\{module_name}\\{contr_name}'
        
    def set_refr_control(self, control_group: Element):
        """ Добавление группы Control в холодильник """
        ref_ctrl_text_map = {
            'ID': '{' + f'{set_new_id(self.exist_control_ids)}' + '}',
            'Left': f'{self.left_coord}',
            'Top': f'{self.top_coord}',
            'Name': f'Холодильное оборудование {self.group_number}',
        }
        set_refr_child_group(
            control_group,
            ref_ctrl,
            ref_ctrl_text_map,
            max_index=8,
            sequence=[0, 1, 2, 5]
        )
    
    def set_refr_properties(self, klogic_xml: KlogicXML, control_group: Element, contr_name: str, type_text: str):
        """ Добавление группы Properties в холодильник """
        ref_prop_text_map = {
            'PathGroup': self.set_tag_path(klogic_xml, contr_name),
            'Type': type_text
        }
        set_refr_child_group(
            control_group[i.properties],
            ref_prop,
            ref_prop_text_map,
            max_index=12,
            sequence=[0, 1]
        )
    
    def set_tag_attrs(self, tag: dict) -> TagAttrs:
        """" Получение атрибутов аварий для визуализации """
        if all([
            tag['alarm_id'] != 'Cutout',
            tag['alarm_id'] != 'None'
        ]):
            tag_attrs = set_alarm_tag_attrs(tag)
        else:
            if tag['kvision_attr'] != 'a45':
                tag_attrs = self.set_kvision_tag_attrs(tag)
        return tag_attrs
    
    def set_refr_passp(self, passps: Element, tag_attrs: TagAttrs, tag_id: str):
        """  Добавление группы passp в холодильник """
        passps.insert(0, get_child_group('Passp', False))
        passp = passps[i.passp]
        passp.insert(
            0,
            get_child_group(
                'Name',
                f'{self.svc_path.replace("$", "")}{tag_id}' + '0000000000000000000000000000000000000000000000'
            )
        )
        passp.insert(1, get_child_group('Type', tag_attrs.type))
        passp.insert(2, get_child_group('Checked', tag_attrs.checked))
    
    def set_param_lists(self, kid: str, gm_mnemo_group: Element, mnemolist_group: Element):
        """ Заполнение групп param_list """
        for param_list in [gm_mnemo_group, mnemolist_group]:
            param_list.insert(0, get_child_group('KLPar', f'{self.svc_path}{kid}'))
        
    def set_refr_tags(self, param_list_mnemolist, group: Element, passps: Element, alarm_and_kvision_tags: List[Iterable]):
        """ Добавление переменных в холодильник """
        for inout in group[i.first_tag:]:
            self.inout_name = inout.attrib['Name']
            for tags in alarm_and_kvision_tags:
                refrigerator_tags = filter(self.filter_tags, tags)
                for tag in refrigerator_tags:
                    if not self.check_cutout(tag):
                        tag_attrs = self.set_tag_attrs(tag)
                        kid, tag_id = self.set_refr_tag_addr(inout)
                        self.logger.debug(
                            str(group.attrib['Name']) + '_' + str(inout.attrib['Name']) + '_' + str(tag_attrs.type))
                        
                        self.set_refr_passp(passps, tag_attrs, tag_id)
                        self.set_param_lists(
                            kid,
                            self.parsed_template_xml.find('.//ParamList'),
                            param_list_mnemolist
                        )
                
                    else:
                        continue
        self.set_param_info_element(kid)
    
    def remove_service_attrs(self):
        """ Удаление служебных символов в XML """
        for control in self.template_controls:
            control.tag = control.tag.split('--')[0]

    def set_gm_mnemo_xml(self, klogic_xml: KlogicXML, mnemolist_xml: MnemoListXML, alarm_tags: Iterable, kvision_tags: Iterable):
        """" Создание мнемосхемы ГМ """
        self.xml_file_name = f'{mnemolist_xml.gm_mnemo_id}.xml'
        self.svc_path = self.set_svc_path(klogic_xml)
        self.template_xml_root.attrib['ID'] = '{' + f'{mnemolist_xml.gm_mnemo_id}' + '}'
        gm = str(klogic_xml.klogic_tree_find().gm.text).split('(')[1].replace(')', '')
        self.set_gm_mnemo_name(gm)
        central_tags = get_central_tags(alarm_tags)
        groups = klogic_xml.module.findall('.//Group')
        self.find_iec_protocol(klogic_xml)

        for self.group_number, group in enumerate(groups):
            if not any([
                check_central(group, central_tags),
                group.attrib['Name'] in ['Служебные теги', 'Дата и время', 'Alarms']
            ]):
                contr_name = group.attrib['Name']
                self.set_new_control(f'{self.group_number}', c.refr_class_id)
                control_group = self.template_controls.find(f'.//Control--{self.group_number}')
                self.set_coordinates()
                prop_type_text = set_refr_type(contr_name)
                
                self.set_refr_control(control_group)
                self.set_refr_properties(klogic_xml, control_group, contr_name, prop_type_text)
                self.cutout_flag = False
                self.set_refr_tags(
                    set_param_list_group(mnemolist_xml.gm_mnemo),
                    group,
                    set_refr_control_xml(control_group, xml_id=mnemolist_xml.gm_mnemo_id),
                    [alarm_tags, kvision_tags]
                )

        self.remove_service_attrs()
        self.set_mnemo_links(klogic_xml, mnemolist_xml)

        self.logger.debug(f'klogic_xml.iec_prot_detected, {klogic_xml.iec_prot_detected}')
        self.logger.debug(self.svc_path)

    def write(self, xml_path):
        self.parsed_template_xml.write(xml_path, encoding='UTF-8')

import pathlib
from typing import Iterable, List
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from dataclasses import dataclass
from .indices import get_index


@dataclass
class NewTagAttrs:
    tag_id: int
    controller: str
    tag_name: str


@dataclass
class GroupAttr:
    name: str
    len_group: int
    addr: int


@dataclass
class ShiftAttrs:
    all_attrs: List[GroupAttr]
    all_lens: set


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


class ErrorCentralAlarm(Exception):
    """ Исключение при отсутствующих авариях у централей 351, 551"""


class Tag:
    """ Класс для параметра"""

    def __init__(self, new_tag_attrs: NewTagAttrs):
        self.tag_attr = new_tag_attrs


def get_tag_value_list(source_tag: Iterable, attr: str):
    for tag in source_tag:
        yield tag[attr]


def get_group_tags(tag: Element) -> list:
    """Получение всех переменных контроллера"""
    central_alarm_len = 35
    group_tag_names = []
    if tag.attrib['Name'] == 'Alarms' and len(tag) > central_alarm_len:
        for alarm_number in range(len(tag))[get_index('first_tag'):]:
            try:
                group_tag_names.append(
                    tag[alarm_number].attrib['Name'].split(f'{alarm_number}_')[get_index('alarm_split')])
            except IndexError:
                raise ErrorCentralAlarm('В группе Alarms у централи добавлены не все переменные')
    else:
        group_tag_names.append(tag.attrib['Name'])
    return group_tag_names


def check_noffl_input(noffl_input: Element) -> bool:
    return (True
            if all([noffl_input.attrib['Name'] != 'N',
                    noffl_input.attrib['Name'] != 'T',
                    noffl_input.attrib['Name'] != 'pOffline'
                    ])
            else False
            )


def tree_insert(parent_group: Element, insert_index: int, child_group: str, text: str):
    child = ElementTree.Element(child_group)
    if text != 'None':
        child.text = text
    parent_group.insert(insert_index, child)


def update_inout_setting(inout: Element, setting_tag: str, text: str):
    for setting in inout[get_index('settings')].iter(setting_tag):
        setting.text = text
        print(setting.tag, text)


def get_node(group: Element) -> str:
    """Получение адреса контроллера"""
    node = 0
    for setting in group[get_index('first_tag')].iter('PropList'):
        node = setting.attrib['Node']
    return node


class KlogicXML:
    """ Класс для  KlogicXML"""

    def __init__(self, xml_path: pathlib.Path, prot_code: str):
        self.xml_path = xml_path
        self.parsed_xml = ElementTree.parse(self.xml_path)
        self.prot_code = prot_code
        self.module = None
        self.new_tag_names = []
        self.new_ids = []
        self.all_new_tags_attrs = []
        self.cental_alarms_flag = False
        self.tag_noffl_flag = False
        self.tag_settings = []  # Список, содержащий данные для заполнения в группе Connected функц.блока noffl
        self.tags_path = []  # Список со строками, содержащими путь к переменным noffl в xml
        self.noffl_contr = 0  # Переменная для подсчета контроллеров, подключенных к функц.блоку noffl
        self.num_of_fb = 0
        self.connected_inputs = 0
        self.teall = '&lt;?xml version=&quot;1.0&quot; encoding=&quot;windows-1251&quot;?&gt;&lt;Elements&gt;&lt;Controls&gt;'

    def find_module(self):
        """Поиск протокола с контроллерами"""
        protocols = self.parsed_xml.findall('.//Protocol')
        for protocol in protocols:
            for setting in protocol.iter('ProtCode'):
                if setting.text == self.prot_code:
                    self.module = protocol[get_index('module')]

    def h_remove(self, attrs: Iterable):
        """Удаление служебных символов в названии параметра"""
        for group in self.module[get_index('first_contr'):]:
            for tag in group[get_index('first_tag'):]:
                for h in attrs:
                    if h in tag.attrib['Name']:
                        tag.attrib['Name'] = tag.attrib['Name'].replace(h, '')

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
        tag_attrs = NewTagAttrs(
            tag_id=self.generate_id(exist_tags),
            controller=group.attrib['Name'],
            tag_name=tag_name
        )
        print('Новый параметр:', tag_attrs.tag_id, tag_attrs.controller, tag_attrs.tag_name)
        return Tag(tag_attrs)

    def update_new_lists(self, new_tag: Tag):
        """Добавление информации о новом теге в соответствующие списки"""
        self.all_new_tags_attrs.append(new_tag.tag_attr)
        self.new_tag_names.append(new_tag.tag_attr.tag_name)
        self.new_ids.append(new_tag.tag_attr.tag_id)

    def get_new_tags(self, exist_tags: Iterable):
        """Проверка на новые переменные"""
        for Group in self.module[get_index('first_contr'):]:
            if not self.cental_alarms_flag:
                for tag in Group[get_index('first_tag'):]:
                    for tag_name in get_group_tags(tag):
                        if tag_name != 'Not used' and self.check_new_tag(exist_tags, tag_name):
                            new_tag = self.create_new_tag(exist_tags, Group, tag_name)
                            self.update_new_lists(new_tag)
            else:
                break

    def set_new_tags(self, exist_tags: Iterable):
        try:
            self.get_new_tags(exist_tags)
            return self.all_new_tags_attrs
        except ErrorCentralAlarm:
            return -1

    def delete_empty_groups(self):
        """Удаление пустых групп"""
        for Group in self.module[get_index('first_contr'):]:
            if len(Group) < 2:
                print("Удалена пустая группа:", Group.attrib['Name'])
                self.module.remove(Group)

    def delete_tags(self, bad_tags: Iterable):
        """Удаление ненужных переменных"""
        central_alarm_len = 35
        for Group in self.module[get_index('first_contr'):]:
            for tag in bad_tags:
                for InOut in Group[get_index('first_tag'):]:
                    if InOut.attrib['Name'] == tag['name'] and len(InOut) < central_alarm_len:
                        print(Group.attrib['Name'], InOut.attrib['Name'], len(InOut))
                        Group.remove(InOut)

    def add_comment(self):
        """Добавление комментария для оборудования"""
        for group in self.module[get_index('first_contr'):]:
            try:
                comm = group.attrib['Name'].split('__')[get_index('contr_name')]
            except KeyError:
                comm = group.attrib['Name']
            settings = group[get_index('settings')]
            for comment in settings.iter('UserComment'):
                comment.text = f'{comm}..{get_node(group)}'

    def klogic_tree_find(self) -> KlogicAttrs:
        """Получение необходимых атрибутов из klogic.xml"""
        kl_find = ()
        protocols = self.parsed_xml.findall('.//Protocol')
        for protocol in protocols:
            for setting in protocol.iter('ProtCode'):
                if setting.text == self.prot_code:
                    self.module = protocol[get_index('module')]
                    kl_find = KlogicAttrs(
                        danfoss=protocol[get_index('settings')][get_index('name')],
                        protocol_name=protocol[get_index('settings')][get_index('name')],
                        gm=protocol[get_index('module')][get_index('settings')][get_index('name')],
                        Groups=protocol[get_index('module')],
                        fsection=self.parsed_xml.find('.//UserTask'),
                        task_name=self.parsed_xml.find('.//UserTask/Settings/Name'),
                        te=self.parsed_xml.find('.//TasksGroup0/UserTask/Settings'),
                        klogic_name=self.parsed_xml.find('.//Controller/Settings/Name'),
                        syst_num=self.parsed_xml.find('.//Controller/Settings/SystNum')
                    )
        return kl_find

    def shift(self) -> ShiftAttrs:
        """Подсчет смещения адресов контроллеров"""
        shift_attr = ShiftAttrs(
            all_attrs=[],
            all_lens=set()
        )
        for group in range(len(self.module))[1:]:
            if all([
                self.module[group].attrib['Name'] != 'Служебные теги',
                self.module[group].attrib['Name'] != 'Дата и время'
            ]):
                shift_attr.all_lens.add(len(self.module[group]))
                for setting in self.module[group][get_index('first_tag')].iter('KId'):
                    contr_attr = GroupAttr(
                        name=self.module[group].attrib['Name'],
                        len_group=len(self.module[group]),
                        addr=setting.text
                    )
                    shift_attr.all_attrs.append(contr_attr)
        return shift_attr

    def get_noffl_tag(self, tag: Element, good_tags: Iterable):
        """Поиск параметра noffl"""
        for good_tag in good_tags:
            if good_tag['noffl']:
                if tag.attrib['Name'] == good_tag['name']:
                    tag_name = tag.attrib['Name']
                    self.tag_noffl_flag = True
                    return tag_name

    def get_noffl_tag_info(self, fb: Element, h: int, good_tags: Iterable):
        """Получение необходимой информации по параметру noffl"""
        kl_find = self.klogic_tree_find()
        groups = kl_find.Groups
        protocol_name = kl_find.protocol_name
        gm = kl_find.gm
        num_of_inputs = 10  # Количество входов в каждом Функциональном блоке noffl

        for fb_input in range(len(fb))[3:]:  # 3 входа ФБ не используются на этом этапе
            if (fb_input + num_of_inputs * h) < len(
                    groups):  # проверка, чтобы текущий номер входа ФБ не превышал кол-во контроллеров
                if (fb_input + 1) == len(fb):  # последний вход ФБ
                    continue
                else:
                    inout = groups[fb_input + num_of_inputs * h]
                    contr = inout.attrib['Name']
                    self.tag_noffl_flag = False
                    for tag in inout[get_index('first_tag'):]:
                        if self.tag_noffl_flag:  # проверка на тот случай, если контроллер уже добавлен в ФБ
                            break
                        tag_name = self.get_noffl_tag(tag, good_tags)
                        if tag_name:
                            self.tag_settings.append(tag[get_index('settings')])
                            st = f'{protocol_name.text}.{gm.text}.{contr}.{tag_name}'
                            self.tags_path.append(st)
            else:
                break

    def create_task_elements(self, in_name: str, task_name: Element, fblock: Element):
        """ Формирование служебной строки <TaskElements> """
        te = f'&lt;ExternalLink&gt;&lt;Path&gt;{task_name.text}.{fblock.text}.{in_name}&lt;/Path&gt;&lt;MarkerLink&gt;&lt;Link&gt;{self.tags_path[self.noffl_contr]}&lt;/Link&gt;&lt;showAllConnections&gt;False&lt;/showAllConnections&gt;&lt;offsetMarkerFB&gt;40&lt;/offsetMarkerFB&gt;&lt;/MarkerLink&gt;&lt;/ExternalLink&gt;'
        self.teall = self.teall + te

    def update_noffl_n(self, fb: Element):
        """Вставка количества контроллеров в ФБ"""
        N_INPUT_INDEX = 5
        if self.connected_inputs > 0:
            setting_text = '%.2f' % self.connected_inputs
        else:
            setting_text = '%.2f' % 0
        update_inout_setting(fb[N_INPUT_INDEX], 'InitValue0', setting_text)

    def update_all_n(self, smart_divide: Element):
        """ Вставка количества контроллеров в ФБ smart divide"""
        print('Общее количество контроллеров:', ((self.num_of_fb - 1) * 10) + self.connected_inputs)
        for inout in smart_divide.iter('InOut'):
            if inout.attrib['Name'] == 'Делитель 1':
                update_inout_setting(inout, 'InitValue0',
                                     '%.2f' % (((self.num_of_fb - 1) * 10) + self.connected_inputs))

    def insert_task_elements(self, kl_find: KlogicAttrs):
        """ Вставка строки <TaskElements> """
        self.teall = self.teall + '&lt;/Controls&gt;&lt;/Elements&gt;'
        settings = kl_find.te
        for index in range(len(settings)):
            if settings[index].tag == 'TaskElements':
                settings.remove(settings[index])
                tree_insert(settings, index, 'TaskElements', self.teall)

    def noffl(self, good_tags: Iterable):
        """Привязка входов к функциональным блокам noffl"""
        kl_find = self.klogic_tree_find()
        groups = kl_find.Groups
        fsection = kl_find.fsection
        task_name = kl_find.task_name
        FIRST_FB_INDEX = 1
        TAG_CONNECTED_INDEX = 0
        FB_INPUT_CONNECTED_INDEX = 1
        num_of_inputs = 10  # Количество входов в каждом Функциональном блоке noffl

        for fb in fsection[FIRST_FB_INDEX:]:
            fblock = fb[get_index('settings')][get_index('name')]  # Название функц.блока
            for h in range(0, 15):
                if fblock.text == f'noffl {h + 1}':
                    self.num_of_fb += 1  # Подсчет функц.блоков noffl
                    self.get_noffl_tag_info(fb, h, good_tags)

                    for noffl_input in fb[get_index('first_fb_input'):]:
                        if (self.noffl_contr + 3) < len(
                                groups):  # len(groups) - общее колличество групп в Klogic XML, включая служебные(3 шт.)
                            if check_noffl_input(noffl_input):
                                in_name = noffl_input.attrib['Name']
                                self.create_task_elements(in_name, task_name, fblock)
                                str_link = f'{task_name.text}.{fblock.text}.{in_name}'

                                ''' Подключение тегов на входы функционального блока '''
                                tree_insert(self.tag_settings[self.noffl_contr], TAG_CONNECTED_INDEX, 'Connected',
                                            str_link)
                                tree_insert(noffl_input[get_index('settings')], FB_INPUT_CONNECTED_INDEX, 'Connected',
                                            self.tags_path[self.noffl_contr])

                                print(str_link, self.tags_path[self.noffl_contr])
                                self.noffl_contr += 1  # Подсчет контроллеров, подключенных к функц.блоку noffl
                        else:
                            break
                    self.connected_inputs = self.noffl_contr - num_of_inputs * (self.num_of_fb - 1)
                    self.update_noffl_n(fb)
                if fblock.text == 'smart divide':
                    smart_divide = fb  # ФБ smart divide
        self.insert_task_elements(kl_find)
        self.update_all_n(smart_divide)

    def write(self, xml_path: pathlib.Path):
        if xml_path == '':
            xml_path = self.xml_path
        self.parsed_xml.write(xml_path)

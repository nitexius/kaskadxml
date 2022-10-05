import pathlib
from typing import Iterable, List
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from dataclasses import dataclass


@dataclass
class NewTagAttrs:
    tag_id: int
    controller: str
    tag_name: str


@dataclass
class ShiftAttrs:
    all_attrs: List[List]
    all_lens: set


@dataclass
class KlogicAttrs:
    danfoss: Element
    gm: Element
    Groups: Element
    fsection: Element
    task_name: Element
    te: Element
    klogic_name: Element
    syst_num: Element


class Tag:
    ''' Класс для параметра'''
    def __init__(self, new_tag_attrs: NewTagAttrs):
        self.tag_attr = new_tag_attrs


def create_tag_value_list(source_tag: Iterable, attr: str):
    for tag in source_tag:
        yield tag[attr]


class KlogicXML:
    ''' Класс для  KlogicXML'''
    def __init__(self, xml_path: pathlib.Path):
        self.xml_path = xml_path
        self.parsed_xml = ElementTree.parse(self.xml_path)
        self.module = None
        self.new_tag_names = []
        self.new_ids = []
        self.all_new_tags_attrs = []
        self.cental_alarms_flag = False
        self.MODULE_INDEX = 1
        self.FIRST_TAG_INDEX = 1
        self.FIRST_CONTR_INDEX = 3
        self.SETTINGS_INDEX = 0
        self.NAME_INDEX = 0

    def find_danfoss_module(self):
        '''поиск протокола danfoss xml'''
        protocols = self.parsed_xml.findall('.//Protocol')
        for protocol in protocols:
            for setting in protocol[self.SETTINGS_INDEX]:
                if all([
                    setting.tag == 'ProtCode',
                    setting.text == '244'
                ]):
                    self.module = protocol[self.MODULE_INDEX]

    def h_remove(self, attrs: Iterable):
        '''удлаение служебных символов в названии параметра'''
        for group in self.module[self.FIRST_CONTR_INDEX:]:
            for tag in group[self.FIRST_TAG_INDEX:]:
                for h in attrs:
                    if h in tag.attrib['Name']:
                        tag.attrib['Name'] = tag.attrib['Name'].replace(h, '')

    def generate_id(self, exist_tags: Iterable) -> int:
        '''Получение нового id'''
        id = 1
        while any([
            id in create_tag_value_list(exist_tags, 'id'),
            id in self.new_ids
        ]):
            id += 1
        return id

    def check_new_tag(self, exist_tags: Iterable, tag_name: str) -> bool:
        '''Проверка нового параметра'''
        return not any([
            tag_name in self.new_tag_names,
            tag_name in create_tag_value_list(exist_tags, 'name')
        ])

    def get_group_tags(self, tag: Element) -> list:
        '''получение всех переменных контроллера'''
        ALARM_SPLIT_INDEX = 1
        Group_tag_names = []
        if tag.attrib['Name'] == 'Alarms' and len(tag) > 35:
            for alarm_number in range(len(tag))[self.FIRST_TAG_INDEX:]:
                try:
                    Group_tag_names.append(
                        tag[alarm_number].attrib['Name'].split(str(alarm_number) + "_")[ALARM_SPLIT_INDEX])
                except IndexError:
                    self.cental_alarms_flag = True
                    break
        else:
            Group_tag_names.append(tag.attrib['Name'])
        return Group_tag_names

    def create_new_tag(self, exist_tags: Iterable, group: Element, tag_name: str) -> Tag:
        '''содание нового тега'''
        tag_attrs = NewTagAttrs(
            tag_id=self.generate_id(exist_tags),
            controller=group.attrib['Name'],
            tag_name=tag_name
        )
        print('Новый параметр:', tag_attrs.tag_id, tag_attrs.controller, tag_attrs.tag_name)
        return Tag(tag_attrs)

    def update_new_lists(self, new_tag: Tag):
        '''добавление информации о новом теге в соответствующие списки'''
        self.all_new_tags_attrs.append(new_tag.tag_attr)
        self.new_tag_names.append(new_tag.tag_attr.tag_name)
        self.new_ids.append(new_tag.tag_attr.tag_id)

    def new_tags(self, exist_tags: Iterable):
        '''Проверка на новые переменные'''
        self.cental_alarms_flag = False

        for Group in self.module[self.FIRST_CONTR_INDEX:]:
            if not self.cental_alarms_flag:
                for tag in Group[self.FIRST_TAG_INDEX:]:
                    for tag_name in self.get_group_tags(tag):
                        if tag_name != 'Not used':
                            if self.check_new_tag(exist_tags, tag_name):
                                new_tag = self.create_new_tag(exist_tags, Group, tag_name)
                                self.update_new_lists(new_tag)
            else:
                break
        result = (
            self.all_new_tags_attrs
            if not self.cental_alarms_flag else -1
        )
        return result

    def delete_tags(self, bad_tags: Iterable):
        '''Удаление ненужных переменных, пустых групп'''
        for Group in self.module[self.FIRST_CONTR_INDEX:]:
            if len(Group) < 2:
                print("Удалена пустая группа:", Group.attrib['Name'])
                self.module.remove(Group)
            for tag in bad_tags:
                for InOut in Group[self.FIRST_TAG_INDEX:]:
                    if InOut.attrib['Name'] == tag['name']:
                        if len(InOut) < 35:
                            print(Group.attrib['Name'], InOut.attrib['Name'], len(InOut))
                            Group.remove(InOut)

    def add_comment(self):
        '''Добавление комментария для оборудования'''
        COMMENT_INDEX = 1
        for Group in self.module[self.FIRST_CONTR_INDEX:]:
            comm = Group.attrib['Name'].replace('__', '..')
            Settings = Group[self.SETTINGS_INDEX]
            UserComment = Settings[COMMENT_INDEX]
            for comment in UserComment.iter('UserComment'):
                comment.text = str(comm)

    def klogic_tree_find(self) -> KlogicAttrs:
        '''Получение необходимых атрибутов из klogic.xml'''
        kl_find = ()
        protocols = self.parsed_xml.findall('.//Protocol')
        for protocol in protocols:
            if protocol[self.SETTINGS_INDEX][self.NAME_INDEX].text == 'Danfoss':
                kl_find = KlogicAttrs(
                    danfoss=protocol[self.SETTINGS_INDEX][self.NAME_INDEX],
                    gm=protocol[self.MODULE_INDEX][self.SETTINGS_INDEX][self.NAME_INDEX],
                    Groups=protocol[self.MODULE_INDEX],
                    fsection=self.parsed_xml.find('.//UserTask'),
                    task_name=self.parsed_xml.find('.//UserTask/Settings/Name'),
                    te=self.parsed_xml.find('.//TasksGroup0/UserTask/Settings'),
                    klogic_name=self.parsed_xml.find('.//Controller/Settings/Name'),
                    syst_num=self.parsed_xml.find('.//Controller/Settings/SystNum')
                )
        return kl_find

    def shift(self) -> ShiftAttrs:
        '''Подсчет смещения адресов контроллеров'''
        shift_attr = ShiftAttrs(
            all_attrs=[],
            all_lens=set()
        )
        for Group in range(len(self.module))[1:]:
            contr_attr = []
            if self.module[Group].attrib['Name'] != 'Служебные теги' and self.module[Group].attrib['Name'] != 'Дата и время':
                contr_attr.append(self.module[Group].attrib['Name'])
                contr_attr.append(len(self.module[Group]))
                shift_attr.all_lens.add(len(self.module[Group]))
                for settings in self.module[Group][1][0]:
                    if settings.tag == 'KId':
                        contr_attr.append(self.module[Group][1].attrib['Name'])
                        contr_attr.append(settings.text)
                shift_attr.all_attrs.append(contr_attr)
        return shift_attr

    def noffl(self, good_tags: Iterable):
        '''Привязка входов к функциональном блокам noffl'''
        kl_find = self.klogic_tree_find()
        danfoss = kl_find.danfoss
        gm = kl_find.gm
        Groups = kl_find.Groups
        fsection = kl_find.fsection
        teall = '&lt;?xml version=&quot;1.0&quot; encoding=&quot;windows-1251&quot;?&gt;&lt;Elements&gt;&lt;Controls&gt;'
        task_name = kl_find.task_name

        FIRST_FB_INDEX = 1
        num_of_inputs = 10  # Количество входов в каждом Функциональном блоке noffl
        strs = []  # Список со строками, содержащими путь к переменным в xml
        tag_settings = []  # Список, содержащий данные для заполнения в группе Connected функц.блока noffl
        num_of_contr = 0  # Переменная для подсчета контроллеров, подключенных к функц.блоку noffl
        num_of_fb = 0  # Переменная для подсчета фнукц.блоков noffl

        for fb in range(len(fsection))[FIRST_FB_INDEX:]:
            fblock = fsection[fb][self.SETTINGS_INDEX][self.NAME_INDEX]  # Название функц.блока
            for h in range(0, 15):
                if fblock.text == f'noffl {h + 1}':
                    num_of_fb = num_of_fb + 1  # Подсчет функц.блоков noffl
                    for fb_input in range(len(fsection[fb]))[3:]:  # 3 входа ФБ не используются на этом этапе
                        if (fb_input + num_of_inputs * h) < len(
                                Groups):  # проверка, чтобы текущий номер входа ФБ не превышал кол-во контроллеров
                            if (fb_input + 1) == len(fsection[fb]):  # последний вход ФБ
                                continue
                            else:
                                inout = Groups[fb_input + num_of_inputs * h]
                                contr = inout.attrib['Name']
                                flag = False
                                for tag in range(len(inout))[self.FIRST_TAG_INDEX:]:
                                    if flag:  # проверка на тот случай, если контроллер уже добавлен в ФБ
                                        break
                                    for good_tag in good_tags:
                                        if good_tag['noffl']:
                                            if inout[tag].attrib['Name'] == good_tag['name']:
                                                tag_setting = inout[tag][0]
                                                tag_settings.append(tag_setting)
                                                tag_name = inout[tag].attrib['Name']
                                                st = f'{danfoss.text}.{gm.text}.{contr}.{tag_name}'
                                                strs.append(st)
                                                flag = True
                        else:
                            break

                    for v in range(len(fsection[fb]))[FIRST_FB_INDEX:]:
                        if (num_of_contr + 3) < len(
                                Groups):  # len(Groups) - общее колличество групп в Klogic XML, включая служебные(3 шт.)
                            noffl_input = fsection[fb][v]  # Вход функционального блока noffl
                            if noffl_input.attrib['Name'] == 'N' or \
                                    noffl_input.attrib['Name'] == 'T' or \
                                    noffl_input.attrib['Name'] == 'pOffline':
                                print(fb, fblock.text, 'v = ', v, noffl_input.attrib['Name'])
                            else:

                                ''' Формирование служебной строки <TaskElements> '''
                                in_name = noffl_input.attrib['Name']
                                str_link = f'{task_name.text}.{fblock.text}.{in_name}'
                                te = f'&lt;ExternalLink&gt;&lt;Path&gt;{task_name.text}.{fblock.text}.{in_name}&lt;/Path&gt;&lt;MarkerLink&gt;&lt;Link&gt;{strs[num_of_contr]}&lt;/Link&gt;&lt;showAllConnections&gt;False&lt;/showAllConnections&gt;&lt;offsetMarkerFB&gt;40&lt;/offsetMarkerFB&gt;&lt;/MarkerLink&gt;&lt;/ExternalLink&gt;'
                                teall = teall + te

                                ''' Подключение тегов на входы функционального блока '''
                                ts = tag_settings[num_of_contr]
                                Connected2 = ElementTree.Element("Connected")
                                Connected2.text = str_link
                                ts.insert(0, Connected2)
                                Connected = ElementTree.Element("Connected")
                                Connected.text = strs[num_of_contr]
                                noffl_input[0].insert(1, Connected)
                                print(fb, 'N =', (num_of_contr - num_of_inputs * (num_of_fb - 1)), str_link,
                                      strs[num_of_contr])
                                num_of_contr = num_of_contr + 1  # Подсчет контроллеров, подключенных к функц.блоку noffl
                        else:
                            break
                    N_input = fsection[fb][5][0]  # Вход ФБ с колличеством подключенных контроллеров
                    connected_inputs = num_of_contr - num_of_inputs * (num_of_fb - 1)
                    N_input.remove(N_input[3])
                    InitValue0 = ElementTree.Element("InitValue0")
                    if connected_inputs > 0:
                        print(N_input[3].text, '%.2f' % connected_inputs)
                        InitValue0.text = '%.2f' % connected_inputs
                    else:
                        InitValue0.text = '%.2f' % 0
                    N_input.insert(3, InitValue0)

                if fblock.text == 'smart divide':
                    smart_divide = fb  # Номер ФБ smart divide

        ''' Вставка строки <TaskElements> '''
        teall = teall + '&lt;/Controls&gt;&lt;/Elements&gt;'
        te = kl_find.te
        for child in range(len(te)):
            if te[child].tag == 'TaskElements':
                te.remove(te[child])
                TaskElements = ElementTree.Element("TaskElements")
                TaskElements.text = teall
                te.insert(child, TaskElements)

        ''' Вставка количества контроллеров в ФБ smart divide'''
        print('Общее количество контроллеров:', ((num_of_fb - 1) * 10) + connected_inputs, 'u=', connected_inputs)
        for t in range(len(fsection[smart_divide]))[1:]:
            if fsection[smart_divide][t].attrib['Name'] == 'Делитель 1':
                all_contr = fsection[smart_divide][t][0]
                all_contr.remove(all_contr[3])
                nall = ((num_of_fb - 1) * 10) + connected_inputs
                InitValueNAll = ElementTree.Element("InitValue0")
                InitValueNAll.text = '%.2f' % nall
                all_contr.insert(3, InitValueNAll)

    def write(self, xml_path: pathlib.Path):
        if xml_path == '':
            xml_path = self.xml_path
        self.parsed_xml.write(xml_path)

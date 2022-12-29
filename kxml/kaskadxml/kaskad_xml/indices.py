from dataclasses import dataclass
from typing import List


@dataclass
class TemplateIdMapAttrs:
    include_tags: List[str]
    exclude_tags: List[str]
    template_id: str
    template_name: str


@dataclass
class ElementAttrs:
    name: str
    text: str


smart_divide_all_n = 'Делитель 1'


template_id_attrs = [
    TemplateIdMapAttrs(include_tags=['u69 Sair Temp', '--- Cutout Temp'], exclude_tags=[], template_id='202b_ct_id',
                       template_name='202B Cutout Temp'),
    TemplateIdMapAttrs(include_tags=['u69 Sair Temp'], exclude_tags=['--- Cutout Temp'], template_id='202b_id',
                       template_name='202B'),
    TemplateIdMapAttrs(include_tags=['--- EKC Error_2'], exclude_tags=[], template_id='202d_id', template_name='202D'),
    TemplateIdMapAttrs(include_tags=['r00 Cutout'], exclude_tags=[], template_id='55_id', template_name='55'),
    TemplateIdMapAttrs(include_tags=['--- Ctrl State'], exclude_tags=[], template_id='550_id', template_name='550'),
    TemplateIdMapAttrs(include_tags=['r57 Po'], exclude_tags=[], template_id='531_id', template_name='531'),
    TemplateIdMapAttrs(include_tags=['Comp_ 8A status'], exclude_tags=[], template_id='551_id', template_name='551'),
    TemplateIdMapAttrs(include_tags=['Comp_ 1 status'], exclude_tags=[], template_id='351_id', template_name='351')
    
]


info_properties = {
            1: ElementAttrs(name='PasInf', text='piMask'),
            2: ElementAttrs(name='MaskInf', text='%d'),
            3: ElementAttrs(name='Transparent', text='False'),
            4: ElementAttrs(name='Layout', text='tlTop'),
            5: ElementAttrs(name='BaseColor', text='16777215'),
            6: ElementAttrs(name='BaseFontColor', text='0'),
            7: ElementAttrs(name='Font.Charset', text='1'),
            8: ElementAttrs(name='Font.Color', text='0'),
            9: ElementAttrs(name='Font.Name', text='Arial'),
            10: ElementAttrs(name='Font.Size', text='8'),
            11: ElementAttrs(name='Font.Style', text='fsBold'),
            12: ElementAttrs(name='BaseFontSize', text='8'),
            13: ElementAttrs(name='AutoSize', text='True'),
            14: ElementAttrs(name='BaseX', text='555'),
            15: ElementAttrs(name='Angle', text='0')
        }


freon_control = {
            1: ElementAttrs(name='Left', text='0'),
            2: ElementAttrs(name='Top', text='0'),
            3: ElementAttrs(name='Width', text='763'),
            4: ElementAttrs(name='Height', text='36'),
            5: ElementAttrs(name='Name', text='Многострочный текст Фреон'),
            6: ElementAttrs(name='Properties', text=False)
        }


freon_properties = {
    0: ElementAttrs(name='NewVer', text='True'),
    1: ElementAttrs(name='NewVer2', text='True'),
    2: ElementAttrs(name='TempFont.Charset', text='1'),
    3: ElementAttrs(name='TempFont.Color', text='16777215'),
    4: ElementAttrs(name='TempFont.Name', text='Arial'),
    5: ElementAttrs(name='TempFont.Size', text='14'),
    6: ElementAttrs(name='TempFont.Style', text='fsBold'),
    7: ElementAttrs(name='BaseFontSize', text='14'),
    8: ElementAttrs(name='BaseFontColor', text='16777215'),
    9: ElementAttrs(name='BaseTransparent', text='False'),
    10: ElementAttrs(name='BaseColor', text='255'),
    11: ElementAttrs(name='BaseCaption', text='В конфигурации Klogic обнаружен протокол ПУ МЭК (датчик утечки фреона)'),
    12: ElementAttrs(name='UseCurrMn', text='False')
}


refrigerator_control = {
    0: ElementAttrs(name='ID', text='ID'),
    1: ElementAttrs(name='Left', text='Left'),
    2: ElementAttrs(name='Top', text='Top'),
    3: ElementAttrs(name='Width', text='100'),
    4: ElementAttrs(name='Height', text='45'),
    5: ElementAttrs(name='Name', text='Name'),
    6: ElementAttrs(name='Properties', text=False),
    7: ElementAttrs(name='ControlXML', text=False)
}


refrigerator_properties = {
    0: ElementAttrs(name='PathGroup', text='PathGroup'),
    1: ElementAttrs(name='Type', text='Type'),
    2: ElementAttrs(name='TempFont.Charset', text='204'),
    3: ElementAttrs(name='TempFont.Color', text='-16777208'),
    4: ElementAttrs(name='TempFont.Name', text='MS Sans Serif'),
    5: ElementAttrs(name='TempFont.Size', text='8'),
    6: ElementAttrs(name='TempFont.Style', text=False),
    7: ElementAttrs(name='SetTempFont.Charset', text='1'),
    8: ElementAttrs(name='SetTempFont.Color', text='-16777208'),
    9: ElementAttrs(name='SetTempFont.Name', text='MS Sans Serif'),
    10: ElementAttrs(name='SetTempFont.Size', text='6'),
    11: ElementAttrs(name='SetTempFont.Style', text='fsBold')
}


xo_types_map = {
    'nt': ['Б', 'БШ', 'НК'],
    'stk': ['СК'],
    'ceh': ['Ц', 'Цех', 'ЦЕХ'],
    'server': ['Серверная', 'СЕРВЕРНАЯ'],
    'central_room': ['МашЗал'],
    'a1k': ['СК', 'НК', 'server']
}


type_names = {
    'B': 'Дискретный вход (Логический)',
    'F': 'Аналоговый вход (Вещественный)',
    'W': 'Аналоговый выход (Целочисленный)'
}

sensor_error_indices = {
    17: 'SdA_se',
    32: 'SsA_se'
}

constants_map = {
    'num_of_inputs': 10,  # Количество входов в каждом Функциональном блоке noffl
    'empty_klogic_group_len': 2,
    'central_alarm_len': 35,
    'new_product_cutout': -50,
    'nt_cutout': -20,
    'stk_cutout': 0,
    'ceh_cutout': 12,
    'server_cutout': 18,
    'brace_l': '{',
    'brace_r': '}',
    'shift_file_name': 'Смещение.txt',
    'chars': '0123456789ABCDEF',
    'mnemo_id_length': [8, 4, 4, 4, 12],
    'id_segmets': {0: 8, 1: 4, 2: 4, 3: 4, 4:12},
    'refr_id_seq': [8, 9, 6, 7],
    'refr_tag_addr_seq': [2, 3, 0, 1],
    'shift_coord': 15,
    'null_id': '00000000-0000-0000-0000-000000000000',
    'refr_class_id': '{98A9BDE2-21A5-47C6-B912-29E6D5B60E93}',
    'info_class_id': '{8DA02C90-D941-4E95-B124-985A995748C0}',
    'str_text_class_id': '{C2F43B73-B94C-45DE-B737-DD48157F94A3}',
    'gm_group_id': '{305FD5B6-033C-4053-A6D4-CC3A6CD35FCC}',
    '55_id': '{BFBF91EB-5F6E-4136-93D7-269E2F7828CB}',
    '551_id': '{6AFD7127-7064-4B83-94FF-C33EBEAD7C50}',
    '351_id': '{63EB0436-E05F-44FE-AE19-D3803AB3720C}',
    '202b_id': '{13C20EA5-539C-4B76-8FFE-39017838E276}',
    '202b_ct_id': '{1C7B8079-635F-414A-B18D-0D9C3D4B91D9}',
    '202d_id': '{BC035DC4-52B4-48E9-BEB6-3169CB23B60F}',
    '550_id': '{8E3849B1-E4E4-4859-BB15-25F0248EFACF}',
    '531_id': '{6255DF31-A077-452B-BD31-3B08A1BA0BE2}',
    'not_virtual_permissions': 'üüüüüü',
    'permissions1': '111111',
    'permissions3': '333333',
    'width': 100,
    'height': 45,
    'shift': 20,
    'max_left_coord': 1700,
    'default_left_coord': 220,
    't_plus': [
        '01', '02', '03', '04', '05', '06', '07', '09', '0A', '0B', '0C', '0D', '0E', '0F',
        '12', '14', '16', '18', '10', '1A', '1C', '1E',
        '21', '24', '25', '28', '29', '20', '2C', '2D',
        '34', '38', '30', '3C', '35', '39', '3D', '31',
        '42', '43', '48', '49', '40', '4A', '4B', '41',
        '52', '58', '50', '5A', '53', '59', '5B', '51',
        '68', '69', '60', '61', '62', '63', '6A', '6B',
        '78', '70', '72', '7A', '73', '7B', '79', '71',
        '82', '83', '84', '85', '86', '87', '80', '81',
        '92', '94', '96', '90', '93', '95', '97', '91',
        'A4', 'A5', 'A0', 'A1', 'A2', 'A3', 'A6', 'A7',
        'B4', 'B0', 'B2', 'B6', 'B3', 'B7', 'B5', 'B1',
        'C2', 'C3', 'C0', 'C1', 'C4', 'C5', 'C6', 'C7',
        'D2', 'D0', 'D3', 'D1', 'D4', 'D6', 'D5', 'D7',
        'E0', 'E1', 'E2', 'E3', 'E4', 'E5', 'E6', 'E7',
        'F0', 'F2', 'F3', 'F4', 'F5', 'F6', 'F7', 'F1',
    ],
    'chars_id_len': 14,    # +1 от словаря
    'chars_id': {
        1: ['35', '39', '3D', '31', '32', '36', '3A', '3E',
            '73', '7B', '74', '7C', 'F7', 'F8'],
        2: ['62', '63', '6A', '6B', '64', '65', '6C', '6D', 'E6',
            'E7', 'E8', 'E9'],
        3: ['53', '59', '5B', '51', '54', '56', '5C', '5E',
            '72', '7A', '75', '7D',
            'D5', 'D7', 'D8', 'DA',
            'F6', 'F9'],
        4: ['C4', 'C5', 'C6', 'C7', 'C8', 'C9', 'CA', 'CB'],
        5: ['79', '71', '76', '7E',
            'B3', 'B7', 'B8', 'BC',
            'D4', 'D6', 'D9', 'DB',
            'F5', 'FA'],
        6: ['A2', 'A3', 'A6', 'A7', 'A8', 'A9', 'AC', 'AD',
            'E4', 'E5', 'EA', 'EB'],
        7: ['93', '95', '97', '91', '98', '9A', '9C', '9E',
            'B2', 'B6', 'B9', 'BD',
            'F4', 'FB'],
        8: [],
        9: ['B5', 'B1', 'BA', 'BE',
            'F3', 'FC', ],
        10: ['E2', 'E3', 'EC', 'ED'],
        11: ['D3', 'D1', 'DC', 'DE',
             'F2', 'FD'],
        12: [],
        13: ['F1', 'FE']
    }
}

indices_map = {
    'alrm_code': 0,
    'alrm_text': 1,
    'group_name': 1,
    'group_alarms': 2,
    'empty_group_len': 4,
    'contr_name': 0,
    'xo_type': 0,
    'product': 1,
    'alarm_index': 0,
    'alarm_id': 0,
    'full_name': 2,
    'station_id': 0,
    'passport_type': 1,
    'group_id': 2,
    'passport_id': 3,
    'value_type': 4,
    'groups_index': 37,
    'grp_name': 0,
    'own_config': 1,
    'params': 2,
    'zone': 0,
    'parid': 1,
    'stid': 2,
    'type': 3,
    'grid': 4,
    'psid': 5,
    'valtype': 6,
    'typename': 7,
    'cipher': 8,
    'klogger_name': 9,
    'usepreagr': 10,
    'module': 1,
    'first_tag': 1,
    'first_contr': 3,
    'first_fb_input': 1,
    'last_noffl_input': 13,
    'first_fb': 1,
    'tag_connected': 0,
    'fb_input_connected': 1,
    'settings': 0,
    'name': 0,
    'alarm_split': 1,
    'service_inputs': 3,
    'n_input_index': 5,
    'me_exist': 3,
    'me_not_exist': 2,
    'first_char': 0,
    'last_id_segment': 12,
    'address': 1,
    'hex_char': 2,
    'templ_char': 0,
    'segm_2': 2,
    'segm_3': 3,
    'segm_4': 4,
    'gm_code': 1,
    'first_passp': 0,
    'control_name': 5,
    'iec_prot_code': '101',
    'properties': 6,
    'control_xml': 7,
    'passps': 1,
    'passp': 0
}


class AttrCreator:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


indices = AttrCreator(**indices_map)
constants = AttrCreator(**constants_map)
xo_types = AttrCreator(**xo_types_map)
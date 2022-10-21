smart_divide_all_n = 'Делитель 1'


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

constants_map = {
    'num_of_inputs': 10,  # Количество входов в каждом Функциональном блоке noffl
    'empty_klogic_group_len': 2,
    'central_alarm_len': 35,
    'new_product_cutout': -50,
    'nt_cutout': -20,
    'stk_cutout': 0,
    'ceh_cutout': 12,
    'server_cutout': 18,
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
    'first_fb': 1,
    'tag_connected': 0,
    'fb_input_connected': 1,
    'settings': 0,
    'name': 0,
    'alarm_split': 1,
    'service_inputs': 3,
    'n_input_index': 5
}


class AttrCreator:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


indices = AttrCreator(**indices_map)
constants = AttrCreator(**constants_map)
xo_types = AttrCreator(**xo_types_map)

from io import BytesIO
from typing import Iterable
from kaskadxml.kaskad_xml import KlogicXML, MnemoListXML


def shift_create(klogic_xml: KlogicXML) -> BytesIO:
    """Подсчет смещения адресов контроллеров"""
    shift_attr = klogic_xml.shift()
    txt = BytesIO()

    for l in shift_attr.all_lens:
        address = 0
        for i, _ in enumerate(shift_attr.all_attrs):
            if shift_attr.all_attrs[i].len_group != l:
                continue
            current_shift = (
                float(shift_attr.all_attrs[i].addr) - address
                if i and address else 0
            )
            address = float(shift_attr.all_attrs[i].addr)
            new_str = f'Кол-во переменных = {l}. {shift_attr.all_attrs[i].name}. Смещение = {current_shift} \n'
            txt.write(bytes(new_str, encoding='utf-8'))
    return txt


def template_log_create(template_log: Iterable) -> BytesIO:
    """  Лог создания мнемосхемы """
    txt = BytesIO()

    new_str = f'Не найден шаблон: \n'
    txt.write(bytes(new_str, encoding='utf-8'))
    for l in template_log:
        if l.no_template:
            new_str = f'------------------------{l.contr_name} \n'
            txt.write(bytes(new_str, encoding='utf-8'))

    new_str = f'Отличающиеся переменные от шаблонов: \n'
    txt.write(bytes(new_str, encoding='utf-8'))
    for l in template_log:
        if l.tags:
            tab = f'\t\t'
            if len(l.contr_name) > 13:
                tab = f'\t'
            new_str = f'------------------------{l.contr_name}{tab}{l.template_name}\t{l.tags} \n'
            txt.write(bytes(new_str, encoding='utf-8'))

    new_str = f'Ошибка привязки виртуальной мнемосхемы: \n'
    txt.write(bytes(new_str, encoding='utf-8'))
    for l in template_log:
        if l.link_error:
            tab = f'\t\t'
            new_str = f'------------------------{l.contr_name} \n'
            txt.write(bytes(new_str, encoding='utf-8'))

    return txt
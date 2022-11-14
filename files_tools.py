import pathlib
import zipfile
from dataclasses import dataclass
from typing import List
from io import BytesIO
from .models import Alarm, Cutout
from .kaskad_xml import KlogicXML, KloggerXML, AlarmsXML, DefaultAlarmError
from .shift_tools import shift_create


@dataclass
class OutputFiles:
    name: str
    file: bytes


def get_klogic_input_file(form):
    PROT_CODE = '244'
    xml_file = form.cleaned_data['klogic_file']
    xml_file_read = xml_file.read()
    klogic_input_file = BytesIO(xml_file_read)
    klogic_input_file.seek(0)
    return KlogicXML(klogic_input_file, PROT_CODE, xml_file.name)


def get_klogger_input_file(args):
    klogger_xml_file = args.form.cleaned_data['klogger_file']
    klogger_xml_file_read = klogger_xml_file.read()
    klogger_input_file = BytesIO(klogger_xml_file_read)
    klogger_input_file.seek(0)
    return KloggerXML(klogger_input_file, args.klogic_xml.klogic_tree_find(), args.station_id, klogger_xml_file.name)


def get_default_alarm_xml_path() -> pathlib.Path:
    try:
        default_alarm_xml_path = Alarm.objects.get(gm='default_alarm_xml').xml.path
    except (Alarm.DoesNotExist, FileNotFoundError):
        raise DefaultAlarmError('Шаблон Alarm XML не найден')
    return default_alarm_xml_path


def get_alarms_input_file(args):
    return AlarmsXML(get_default_alarm_xml_path(), args.klogic_xml.klogic_tree_find(), args.station_id,
                     Cutout.get_products_values())


def create_output_file(kaskad_module: KlogicXML or AlarmsXML or KloggerXML) -> OutputFiles:
    output_file = BytesIO()
    kaskad_module.write(output_file)
    return OutputFiles(
        name=kaskad_module.xml_file_name,
        file=output_file.getbuffer()
    )


def create_shift_output_file(klogic_xml):
    return OutputFiles(
        name='Смещение.txt',
        file=shift_create(klogic_xml).getbuffer()
    )


def get_files(input_file, output_file, args):
    file = input_file(args)
    return output_file(file, args)


def set_arch(zip_buffer: BytesIO, files: List[OutputFiles]) -> BytesIO:
    for file in files:
        with zipfile.ZipFile(zip_buffer, 'a') as zip_file:
            zip_file.writestr(file.name, file.file)
    return zip_buffer

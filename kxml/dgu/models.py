from django.db import models
from .kaskad_xml import alrm


TAG_TYPES = (
    ('1', 'good_tag'),
    ('2', 'bad_tag'),
    ('3', 'new_tag'),
)


class Alarm_dgu(models.Model):
    """Xml Аварии ИС Диспетчеризация ХО"""
    gm = models.CharField(max_length=100, verbose_name='Код ГМ', unique=True)
    xml = models.FileField(upload_to='media/alarms')

    class Meta:
        ordering = ['gm']
        verbose_name = 'Alarm'
        verbose_name_plural = 'Alarms'

    def __str__(self):
        return self.gm


class Dgu_tag(models.Model):
    """Используемые переменные"""
    name = models.CharField(max_length=100, verbose_name='Название переменной', unique=True)
    tag_type = models.CharField(
        max_length=100,
        verbose_name='Тип переменной',
        choices=TAG_TYPES
    )
    alarm_id = models.CharField(max_length=100, default='None', verbose_name='Код аварии', choices=alrm)
    bdtp = models.BooleanField(default=False, verbose_name='Архивируемая переменная')
    noffl = models.BooleanField(default=False, verbose_name='ФБ noffl')
    controller = models.CharField(max_length=100, default="", verbose_name='Адрес переменной')
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Переменная'
        verbose_name_plural = 'Переменные'

    @classmethod
    def get_tags_names(cls):
        return cls.objects.exclude(tag_type='3').values('id', 'name')

    @classmethod
    def get_alarm_tags(cls):
        return cls.objects.exclude(alarm_id__in=['0', 'None']).values('name', 'alarm_id')

    def __str__(self):
        return self.name

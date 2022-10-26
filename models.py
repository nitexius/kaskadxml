from django.db import models
from .kaskad_xml import alrm, xo_choices


class Alarm(models.Model):
    """Xml Аварии ИС Диспетчеризация ХО"""
    gm = models.CharField(max_length=100, verbose_name='Код ГМ', unique=True)
    xml = models.FileField(upload_to='media/alarms')

    class Meta:
        ordering = ['gm']
        verbose_name = 'Alarm'
        verbose_name_plural = 'Alarms'

    def __str__(self):
        return self.gm


class Cutout(models.Model):
    """Уставки для продуктов (Контроль уставок)"""
    name = models.CharField(max_length=100, verbose_name='Наименование продукта', unique=True)
    cutout = models.IntegerField(default=-50, verbose_name='Уставка')
    xo_type = models.CharField(max_length=100, default='None', verbose_name='Серверная/Машзал', choices=xo_choices)

    class Meta:
        ordering = ['name']
        verbose_name = 'Контроль уставок'
        verbose_name_plural = 'Контроль уставок'

    @classmethod
    def get_products_values(cls):
        products = list(cls.objects.all().values())
        return products

    def __str__(self):
        return self.name


class HistoryAttr(models.Model):
    """Служебные символы в названии переменной"""
    h_attr = models.CharField(max_length=30)

    class Meta:
        ordering = ['h_attr']
        verbose_name = '[H_   ]'
        verbose_name_plural = '[H_   ]'

    @classmethod
    def get_h_attrs(cls):
        result = []
        for h in cls.objects.all():
            attr = h.h_attr
            attr = attr.replace('"', "")
            result.append(attr)
        return result

    def __str__(self):
        return self.h_attr


class TagType(models.Model):
    tag_type = models.CharField(max_length=100, default='new_tag', verbose_name='Тип переменной', unique=True)

    class Meta:
        ordering = ['tag_type']
        verbose_name = 'Тип переменной'
        verbose_name_plural = 'Типы переменных'

    def __str__(self):
        return self.tag_type


class Tag(models.Model):
    """Используемые переменные"""
    name = models.CharField(max_length=100, verbose_name='Название переменной', unique=True)
    tag_type = models.ForeignKey(TagType, on_delete=models.SET_NULL, null=True)
    alarm_id = models.CharField(max_length=100, default='None', verbose_name='Код аварии', choices=alrm)
    bdtp = models.BooleanField(default=False, verbose_name='Архивируемая переменная')
    noffl = models.BooleanField(default=False, verbose_name='ФБ noffl')
    controller = models.CharField(max_length=100, default="", verbose_name='Название контроллера')

    class Meta:
        ordering = ['name']
        verbose_name = 'Переменная'
        verbose_name_plural = 'Переменные'

    @classmethod
    def get_tags_values(cls):
        tags = list(cls.objects.all().values())
        return tags

    @classmethod
    def get_bdtp_tags(cls):
        bdtp_tags = list(cls.objects.filter(bdtp='1').values())
        return bdtp_tags

    @classmethod
    def get_bad_tags(cls):
        bad_tags = list(cls.objects.filter(tag_type='2').values())
        return bad_tags

    @classmethod
    def delete_new_tags(cls):
        new_tags = cls.objects.filter(tag_type='3')
        for tag in new_tags:
            tag.delete()

    def __str__(self):
        return self.name

from django import forms


class DguForm(forms.Form):
    station = forms.CharField(max_length=10, label='Номер станции', required=False)
    protocol_name = forms.CharField(max_length=100, label='Название протокола (ГМ)', required=False)
    klogic_file = forms.FileField(label='Klogic XML')
    alarm = forms.BooleanField(label='Сформировать Alarms XML', required=False)

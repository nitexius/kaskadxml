from django import forms


class KlogicForm(forms.Form):
    station = forms.CharField(label='Номер станции')
    klogic_file = forms.FileField(label='Klogic XML')
    bd = forms.BooleanField(label='Сформировать Klogger XML', required=False)
    klogger_file = forms.FileField(label='Klogger XML', required=False)
    alarm = forms.BooleanField(label='Сформировать Alarms XML', required=False)

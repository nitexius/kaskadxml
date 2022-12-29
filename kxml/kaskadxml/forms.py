from django import forms


class KlogicForm(forms.Form):
    station = forms.CharField(max_length=10, label='Номер станции', required=False)
    klogic_file = forms.FileField(label='Klogic XML')
    bd = forms.BooleanField(label='Сформировать Klogger XML', required=False)
    klogger_file = forms.FileField(label='Klogger XML', required=False)
    alarm = forms.BooleanField(label='Сформировать Alarms XML', required=False)
    mnemolist = forms.BooleanField(label='Сформировать мнемосхему ГМ', required=False)
    mnemolist_file = forms.FileField(label='Mnemolist XML', required=False)

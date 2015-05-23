# coding=utf-8
from django.forms.extras import SelectDateWidget

__author__ = 'Basa'


# encoding:utf-8
from django.forms import ModelForm, CheckboxSelectMultiple, ModelChoiceField
from django import forms

FORMAS_PAGO = ((1, 'Cuenta Corriente'),
               (2, 'Contado'),
                (3, 'Otras formas de pago'))

CODIGOS_REMOTOS = ((1, 'Chaco'),
                   (2, 'Corrientes'))

MAS_FORMASDEPAGO = ((6, 'Compensacion'),
                     (8, 'Reposicion'),
                    (7, 'Cortesias'),
                    (5, 'Otros'))

PROMOCIONES = (('2 publicaciones = 1 sin cargo', '2 publicaciones = 1 sin cargo'),
                ('3 publicaciones = 1 sin cargo', '3 publicaciones = 1 sin cargo'),
                ('3 publicaciones = 1 sin cargo(2x2)', '3 publicaciones = 1 sin cargo(2x2)'),
                ('4 o mas días 50% descuento', '4 o mas días 50% descuento'),
                ('5 publicaciones = 1 Sin cargo', '5 publicaciones = 1 Sin cargo'),
                ('7 publicaciones = 3 sin cargo', '7 publicaciones = 3 sin cargo'),
                ('Agencias publican 3 = 1 sin cargo', 'Agencias publican 3 = 1 sin cargo'),
                ('Promo Agencia y Cliente', 'Promo Agencia y Cliente'),
                ('Cámara de Automotores', 'Cámara de Automotores'),
                ('Cámara Inmobiliaria', 'Cámara Inmobiliaria'),
                ('Sin Promoción', 'Sin Promoción'))



REPORTES_CC =((1, 'Hoy'),
              (2, 'Otros'))

class DatosEntradaScriptForm(forms.Form):
    fechaDesde = forms.DateField(label='Ingrese la fecha desde:')#,  widget = SelectDateWidget(years=range(2013, 2000, -1)))  #

    fechaHasta = forms.DateField(label='Ingrese la fecha hasta:')#,
                                 #widget=SelectDateWidget(years=range(2013, 2000, -1)))  #

    formaDePago = forms.ChoiceField(label='Ingrese forma de pago:', widget=forms.RadioSelect,
                                            choices=FORMAS_PAGO)  #


    formaDePagoMas = forms.MultipleChoiceField(widget=CheckboxSelectMultiple, choices=MAS_FORMASDEPAGO, required=False)

    # reporte = forms.ChoiceField(label='Seleccione el reporte que desea cargar', choices=[(x, x) for x in ('Contado', 'Ventas totales de Contado')])#, 'Interior', 'Capital', 'Ventura', 'Oficiales', 'Canjes', 'Directas')])


    codRemoto = forms.ChoiceField(label='Ingrese codigo remoto:', widget=forms.RadioSelect,
                                  choices=CODIGOS_REMOTOS)  # label='Ingrese codigo remoto:',widget=forms.RadioSelect,
    # reporte = forms.ChoiceField(label='Seleccione el reporte que desea cargar', widget=forms.RadioSelect,
    #                             choices=REPORTES_CC)



class formLogin(forms.Form):
    username = forms.CharField(label='Usuario')  #
    password = forms.CharField(label='Password', widget=forms.PasswordInput)  #

class formTotalVentaPublicidad(forms.Form):
    fechaDesde = forms.DateField(label='Ingese la fecha desde:')
    fechaHasta = forms.DateField(label='Ingese la fecha hasta:')
    codRemoto = forms.ChoiceField(label='Ingrese codigo remoto:', widget=forms.RadioSelect,
                                  choices=CODIGOS_REMOTOS)

class formVentaNetaAnual(forms.Form):
    codRemoto = forms.ChoiceField(label='Ingrese codigo remoto:', widget=forms.RadioSelect,
                                  choices=CODIGOS_REMOTOS)

class formPromociones(DatosEntradaScriptForm):
    formaDePago = forms.ChoiceField(label='Ingrese forma de pago:', widget=forms.RadioSelect,
                                            choices=FORMAS_PAGO, required=False)  #


    formaDePagoMas = None

    codRemoto = forms.ChoiceField(label='Ingrese codigo remoto:', widget=forms.RadioSelect,
                                  choices=CODIGOS_REMOTOS, required=False)



class formVentasCaptura(formPromociones):
    fechaDesde = forms.DateField(label='Ingese la fecha desde:', required=False)
    fechaHasta = forms.DateField(label='Ingese la fecha hasta:', required=False)

    formaDePago = forms.ChoiceField(label='Ingrese forma de pago:', widget=forms.RadioSelect,
                                        choices=FORMAS_PAGO, required=False)  #

    hoy = forms.ChoiceField(widget=CheckboxSelectMultiple ,required=False)


    formaDePagoMas = None


"""
Formulario de pago SIMULADO. No se cobra nada ni se guarda el número de tarjeta:
solo sus últimos 4 dígitos para el historial.
"""
import re

from django import forms
from django.utils import timezone

from .models import Compra

TARJETA_RECHAZADA = '0000'   # una tarjeta terminada en 0000 simula un pago rechazado


def solo_digitos(texto):
    return re.sub(r'\D', '', texto or '')


class PagoForm(forms.Form):
    metodo = forms.ChoiceField(label='Método de pago', choices=Compra.METODOS, widget=forms.RadioSelect,
                               initial=Compra.TARJETA)

    # Tarjeta
    tarjeta_numero = forms.CharField(
        label='Número de tarjeta', required=False, max_length=23,
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'cc-number',
                                      'placeholder': '0000 0000 0000 0000'}))
    tarjeta_vence = forms.CharField(
        label='Vencimiento', required=False, max_length=5,
        widget=forms.TextInput(attrs={'autocomplete': 'cc-exp', 'placeholder': 'MM/AA'}))
    tarjeta_cvv = forms.CharField(
        label='CVV', required=False, max_length=4,
        help_text='Los 3 o 4 números al reverso de tu tarjeta.',
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'cc-csc', 'placeholder': '123'}))

    # Yape y Plin
    celular = forms.CharField(
        label='Celular asociado', required=False, max_length=15,
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'tel', 'placeholder': '9XX XXX XXX'}))
    codigo_yape = forms.CharField(
        label='Código de aprobación de Yape', required=False, max_length=6,
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'placeholder': '6 dígitos'}))

    def clean(self):
        datos = super().clean()
        metodo = datos.get('metodo')

        if metodo == Compra.TARJETA:
            numero = solo_digitos(datos.get('tarjeta_numero'))
            if len(numero) != 16:
                self.add_error('tarjeta_numero', 'El número de tarjeta debe tener 16 dígitos.')
            vence = (datos.get('tarjeta_vence') or '').strip()
            coincide = re.fullmatch(r'(0[1-9]|1[0-2])/(\d{2})', vence)
            if not coincide:
                self.add_error('tarjeta_vence', 'Escribe el vencimiento como MM/AA, por ejemplo 08/29.')
            else:
                mes, anio = int(coincide[1]), 2000 + int(coincide[2])
                hoy = timezone.localdate()
                if (anio, mes) < (hoy.year, hoy.month):
                    self.add_error('tarjeta_vence', 'Esta tarjeta ya venció.')
            if not re.fullmatch(r'\d{3,4}', (datos.get('tarjeta_cvv') or '').strip()):
                self.add_error('tarjeta_cvv', 'El CVV tiene 3 o 4 números.')
            if not self.errors and numero.endswith(TARJETA_RECHAZADA):
                raise forms.ValidationError(
                    'Tu banco rechazó el pago. Prueba con otra tarjeta o paga con Yape o Plin.')
            datos['detalle_pago'] = f'Tarjeta terminada en {numero[-4:]}'

        elif metodo in (Compra.YAPE, Compra.PLIN):
            celular = solo_digitos(datos.get('celular'))
            if not re.fullmatch(r'9\d{8}', celular):
                self.add_error('celular', 'Ingresa un celular de 9 dígitos que empiece con 9.')
            if metodo == Compra.YAPE and not re.fullmatch(r'\d{6}', (datos.get('codigo_yape') or '').strip()):
                self.add_error('codigo_yape', 'El código de aprobación tiene 6 dígitos.')
            nombre = 'Yape' if metodo == Compra.YAPE else 'Plin'
            datos['detalle_pago'] = f'{nombre} desde el celular terminado en {celular[-3:]}'

        return datos

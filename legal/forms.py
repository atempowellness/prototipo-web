import re

from django import forms

from .models import Reclamacion


class ReclamacionForm(forms.ModelForm):
    acepto = forms.BooleanField(
        label='Declaro que los datos consignados son verdaderos.',
        error_messages={'required': 'Para enviar la hoja necesitas confirmar que los datos son verdaderos.'})

    class Meta:
        model = Reclamacion
        fields = ['nombre', 'dni', 'domicilio', 'telefono', 'email',
                  'servicio', 'monto', 'descripcion_servicio', 'tipo', 'detalle', 'pedido']
        labels = {'monto': 'Monto reclamado (S/, opcional)'}
        help_texts = {
            'descripcion_servicio': 'Por ejemplo: "Paquete Atempo 10 comprado el 20/09" o "Clase de Pilates del 25/09".',
            'detalle': 'Cuéntanos qué pasó, con la mayor cantidad de detalles posible.',
            'pedido': '¿Qué solución esperas del estudio?',
        }
        widgets = {
            'tipo': forms.RadioSelect,
            'detalle': forms.Textarea(attrs={'rows': 5}),
            'pedido': forms.Textarea(attrs={'rows': 3}),
            'dni': forms.TextInput(attrs={'inputmode': 'numeric'}),
            'telefono': forms.TextInput(attrs={'inputmode': 'numeric', 'autocomplete': 'tel'}),
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
            'nombre': forms.TextInput(attrs={'autocomplete': 'name'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['servicio'].choices = [('', 'Elige una opción')] + Reclamacion.SERVICIOS
        self.fields['tipo'].choices = Reclamacion.TIPOS

    def clean_dni(self):
        dni = re.sub(r'\D', '', self.cleaned_data['dni'])
        if not re.fullmatch(r'\d{8}', dni):
            raise forms.ValidationError('Ingresa un DNI de 8 dígitos.')
        return dni

    def clean_telefono(self):
        telefono = re.sub(r'\D', '', self.cleaned_data['telefono'])
        if len(telefono) < 7:
            raise forms.ValidationError('Ingresa un teléfono válido.')
        return telefono

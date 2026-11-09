from django import forms


class StyledFormMixin:
    """Adds the design-system CSS classes to every widget of a form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                css = 'check'
            elif isinstance(widget, forms.FileInput):
                css = 'file-input'
            else:
                css = 'input'
            widget.attrs['class'] = f"{widget.attrs.get('class', '')} {css}".strip()

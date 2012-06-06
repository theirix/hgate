from django import template
register = template.Library()

@register.filter
def field_class(form, field):
    return form.classes[field.name]
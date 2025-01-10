from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """ Get an item from a dictionary by key """
    try:
        return dictionary.get(key, None)
    except AttributeError:
        return None
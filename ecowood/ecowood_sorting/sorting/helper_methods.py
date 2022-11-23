from odoo import _


def display_popup_message(title="title", message="message", sticky=False, display_type="info"):
    """
    :param title: title of your warning
    :param message: message of your warning
    :param sticky: if message is displayed as a sticky
    :param display_type:  success,warning,danger,info
    """
    title = _(title)
    message = _(message)
    return {
        'type': 'ir.actions.client',
        'tag': 'display_notification',
        'params': {
            'title': title,
            'message': message,
            'sticky': sticky,
            'type': display_type,

        }
    }
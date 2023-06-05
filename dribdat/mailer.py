# -*- coding: utf-8 -*-
"""Helper for sending mail."""
from flask import url_for, current_app
from flask_mailman import EmailMessage
from dribdat.utils import random_password  # noqa: I005
import logging


def user_activation(user):
    """Send an activation by e-mail."""
    act_hash = random_password(32)
    user.set_hashword(act_hash)
    user.save()
    base_url = url_for('public.home', _external=True)
    act_url = url_for(
        'auth.activate',
        userid=user.id,
        userhash=act_hash,
        _external=True)
    if not 'mailman' in current_app.extensions:
        logging.warning('E-mail extension has not been configured')
        return act_hash
    msg = EmailMessage()
    msg.subject = 'Your dribdat account'
    msg.body = \
        "Hello %s,\n" % user.username \
        + "Thanks for signing up at %s\n\n" % base_url \
        + "Tap here to activate your account:\n\n%s" % act_url
    msg.to = [user.email]
    logging.info('Sending activation mail to user %d' % user.id)
    logging.debug(act_url)
    msg.send(fail_silently=True)
    return act_hash

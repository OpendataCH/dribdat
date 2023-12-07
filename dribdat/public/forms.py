# -*- coding: utf-8 -*-
"""Public facing forms."""

from flask_wtf import FlaskForm
from wtforms import (
    SubmitField, BooleanField,
    StringField, TextAreaField,
    SelectField, HiddenField,
)
from wtforms.fields import (
    TimeField, DateField,
    URLField,
)
# from wtforms_html5 import AutoAttrMeta
from wtforms.validators import DataRequired, length
from ..user.validators import UniqueValidator
from dribdat.user.models import Project, Event
from datetime import time, datetime


class ProjectNew(FlaskForm):
    """Create a project form."""

    id = HiddenField('id')
    autotext_url = URLField(
        u'Sync from (Readme)', [length(max=2048)],
        description="[Optional] Link to a repository or documentation "
        + "of your project.")
    name = StringField(
        u'Title',
        [length(max=80), UniqueValidator(Project, 'name'), DataRequired()],
        description=u"A short project title or team name - you may change "
        + "this later.")
    summary = StringField(
        u'Summary', [length(max=140)],
        description="The headline of your project, in up to 140 characters.")
    generate_pitch = BooleanField(u"Use AI to auto-generate a pitch")
    category_id = SelectField(
        u'Category', coerce=int, description=u"Select the category that your "
        + " challenge addresses.")
    contact_url = StringField(
        u'Contact', [length(max=2048)],
        description="On which channel, or in which room, to find you.")
    template = HiddenField('template')
    submit = SubmitField(u'Save')


class ProjectForm(FlaskForm):
    """Edit a project form."""

    id = HiddenField('id')
    name = StringField(
        u'Title',
        [length(max=80), UniqueValidator(Project, 'name'), DataRequired()],
        render_kw={'maxlength': 80, 'required': 'required'},
        description="A short project name, max 80 characters.")
    summary = StringField(
        u'Summary', [length(max=140)],
        render_kw={'maxlength': 140},
        description="The headline of your project, in up to 140 characters.")
    longtext = TextAreaField(
        u'Pitch',
        description="To format, use Markdown or HTML. Links to Speaker Deck"
        + " and many other sites (oembed.com) get a live preview.")
    webpage_url = URLField(
        u'Demo link', [length(max=2048)],
        description="URL to a live demo, presentation, or a link to get "
        + "more information.")
    is_webembed = BooleanField(u'Embed this link directly on project page')
    submit = SubmitField(u'Save changes')
    note = TextAreaField(
        u'Log entry',
        [length(max=280)],
        render_kw={'maxlength': 280, 'rows': 3},
        description=u'(Optional) A short update for the project log')


class ProjectDetailForm(FlaskForm):
    """Edit a project detail form."""

    id = HiddenField('id')
    category_id = SelectField(u'Challenge category', coerce=int)
    autotext_url = URLField(
        u'Readme', [length(max=255)],
        description="Code, wiki or an online document to Sync with.")
    source_url = URLField(
        u'Sources', [length(max=255)],
        description="Link to source code repository or project data.")
    download_url = URLField(
        u'Download', [length(max=255)],
        description="Link to a release page to get a copy of your project.")
    contact_url = StringField(
        u'Contact us', [length(max=255)],
        description="Link to an issues page, contact form, forum thread, etc.")
    hashtag = StringField(
        u'Hashtag', [length(max=255)],
        description="Team channel or social media hashtag.")
    # Note: relative links allowed in image_url -> StringField
    image_url = StringField(
        u'Cover image', [length(max=255)],
        description="URL of an image to display at the top of the page.")
    logo_color = StringField(
        u'Color scheme',
        description="Customize the color of your project page.")
    logo_icon = StringField(
        u'Named icon',
        [length(max=20)], description='Select an icon from FontAwesome'
        + ': https://fontawesome.com/v4/cheatsheet')
    submit = SubmitField(u'Save changes')


class ProjectPost(FlaskForm):
    """Add a post to a project."""

    id = HiddenField('id')
    has_progress = BooleanField(u"Let's go!")
    note = TextAreaField(
        u'What are you working on right now?',
        [length(max=280), DataRequired()],
        render_kw={'maxlength': 280},
        description=u'A short note for your project log.')
    submit = SubmitField(u'Save post')


class ProjectComment(FlaskForm):
    """Add a comment to a project."""

    id = HiddenField('id')
    note = TextAreaField(
        u'Comments and reviews',
        [length(max=280), DataRequired()],
        render_kw={'maxlength': 280},
        description=u'A suggestion or constructive feedback for the team.'
                    + ' Please note the Code of Conduct.')
    submit = SubmitField(u'Save comment')


class ProjectBoost(FlaskForm):
    """Add a boost to a project."""

    id = HiddenField('id')
    note = TextAreaField(u'Short praise and comments', [
                         length(max=280), DataRequired()])
    boost_type = SelectField(u'Select booster pack', [DataRequired()])
    submit = SubmitField(u'Energize!')


class NewEventForm(FlaskForm):
    """Add a new Event."""

    next = HiddenField()
    id = HiddenField('id')
    name = StringField(
        u'Title',
        [length(max=80), UniqueValidator(Event, 'name'), DataRequired()])
    starts_date = DateField(u'Starting date', default=datetime.now())
    starts_time = TimeField(u'Starting time', default=time(9, 0, 0))
    ends_date = DateField(u'Finish date', default=datetime.now())
    ends_time = TimeField(u'Finish time', default=time(16, 0, 0))
    summary = StringField(
        u'Summary',
        [length(max=140)],
        description=u'A short overview (140 chars) of the upcoming event')
    hostname = StringField(
        u'Hosted by', [length(max=80)],
        description=u'Organization responsible for the event')
    location = StringField(
        u'Located at', [length(max=255)],
        description=u'The event locale or virtual space')
    hashtags = StringField(
        u'Hashtags', [length(max=255)],
        description=u'Social media hashtags for this event')
    description = TextAreaField(
        u'Description', description=u'Markdown and HTML supported')
    logo_url = URLField(
        u'Host logo link', [length(max=255)],
        description=u'Link to a small logo file (max 688x130)')
    gallery_url = URLField(
        u'Gallery links',
        [length(max=2048)],
        description=u'URL to large background image (max 1920x1080)')
    webpage_url = URLField(
        u'Home page link', [length(max=255)],
        description=u'Link to register and get information about the event')
    community_url = URLField(
        u'Community link', [length(max=255)],
        description=u'Link to connect to a community forum or hashtag')
    submit = SubmitField(u'Save')

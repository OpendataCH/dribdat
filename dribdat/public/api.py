 # -*- coding: utf-8 -*-

from flask import Blueprint, render_template, redirect, url_for, make_response, request, flash, jsonify, current_app
from flask_login import login_required, current_user

from sqlalchemy import or_

from ..extensions import db
from ..utils import timesince, random_password

from ..user.models import Event, Project, Category, Activity
from ..aggregation import GetProjectData

from datetime import datetime
from flask import Response, stream_with_context

import io, csv, json, sys, tempfile
from os import path
PY3 = sys.version_info[0] == 3

blueprint = Blueprint('api', __name__, url_prefix='/api')

def get_projects_by_event(event_id):
    return Project.query.filter_by(event_id=event_id, is_hidden=False)

def get_project_summaries(projects):
    summaries = expand_project_urls([ p.data for p in projects ])
    summaries.sort(key=lambda x: x['score'], reverse=True)
    return summaries

# Collect all projects and challenges for an event
def project_list(event_id):
    projects = get_projects_by_event(event_id)
    return get_project_summaries(projects)

# Generate a CSV file
def gen_csv(csvdata):
    if len(csvdata) < 1: return ""
    headerline = csvdata[0].keys()
    if PY3:
        output = io.StringIO()
    else:
        output = io.BytesIO()
        headerline = [l.encode('utf-8') for l in headerline]
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerow(headerline)
    for rk in csvdata:
        rkline = []
        for l in rk.values():
            if l is None:
                rkline.append("")
            elif isinstance(l, (int, float, datetime, str)):
                rkline.append(str(l))
            elif isinstance(l, (dict)):
                rkline.append(json.dumps(l))
            else:
                rkline.append(l.encode('utf-8'))
        writer.writerow(rkline)
    return output.getvalue()

# ------ EVENT INFORMATION ---------

# API: Outputs JSON about the current event
@blueprint.route('/event/current/info.json')
def info_current_event_json():
    event = Event.query.filter_by(is_current=True).first() or \
            Event.query.order_by(Event.id.desc()).first_or_404()
    return jsonify(event=event.data, timeuntil=timesince(event.countdown, until=True))

# API: Outputs JSON about an event
@blueprint.route('/event/<int:event_id>/info.json')
def info_event_json(event_id):
    event = Event.query.filter_by(id=event_id).first_or_404()
    return jsonify(event=event.data, timeuntil=timesince(event.countdown, until=True))

# API: Outputs JSON-LD about an Event according to https://schema.org/Hackathon
@blueprint.route('/event/<int:event_id>/hackathon.json')
def info_event_hackathon_json(event_id):
    event = Event.query.filter_by(id=event_id).first_or_404()
    return jsonify(event.get_schema(request.host_url))

# ------ EVENT PROJECTS ---------

# API: Outputs JSON of projects in the current event, along with its info
@blueprint.route('/event/current/projects.json')
def project_list_current_json():
    event = Event.query.filter_by(is_current=True).first() or \
            Event.query.order_by(Event.id.desc()).first_or_404()
    return jsonify(projects=project_list(event.id), event=event.data)

# API: Outputs JSON of all projects at a specific event
@blueprint.route('/event/<int:event_id>/projects.json')
def project_list_json(event_id):
    return jsonify(projects=project_list(event_id))

def project_list_csv(event_id, event_name):
    return Response(stream_with_context(gen_csv(project_list(event_id))),
                    mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=' + event_name + '_dribdat.csv'})

# API: Outputs CSV of all projects in an event
@blueprint.route('/event/<int:event_id>/projects.csv')
def project_list_event_csv(event_id):
    event = Event.query.filter_by(id=event_id).first_or_404()
    return project_list_csv(event.id, event.name)

# API: Outputs CSV of projects and challenges in the current event
@blueprint.route('/event/current/projects.csv')
def project_list_current_csv():
    event = Event.query.filter_by(is_current=True).first() or \
            Event.query.order_by(Event.id.desc()).first_or_404()
    return project_list_csv(event.id, event.name)

# API: Outputs JSON of categories in the current event
@blueprint.route('/event/current/categories.json')
def categories_list_current_json():
    event = Event.query.filter_by(is_current=True).first()
    return jsonify(categories=[ c.data for c in event.categories_for_event() ], event=event.data)

# ------ ACTIVITY FEEDS ---------

def get_event_activities(event_id, limit=50):
    event = Event.query.filter_by(id=event_id).first_or_404()
    return [a.data for a in Activity.query
              .filter(Activity.timestamp>=event.starts_at)
              .order_by(Activity.id.desc()).limit(limit).all()]

# API: Outputs JSON of recent activity in an event
@blueprint.route('/event/<int:event_id>/activity.json')
def event_activity_json(event_id):
    limit = request.args.get('limit') or 50
    return jsonify(activities=get_event_activities(event_id, limit))

# API: Outputs JSON of categories in the current event
@blueprint.route('/event/current/activity.json')
def event_activity_current_json():
    event = Event.query.filter_by(is_current=True).first()
    if not event: return jsonify(activities=[])
    return event_activity_json(event.id)

# API: Outputs CSV of an event activity
@blueprint.route('/event/<int:event_id>/activity.csv')
def event_activity_csv(event_id):
    limit = request.args.get('limit') or 50
    return Response(stream_with_context(gen_csv(get_event_activities(event_id, limit))),
                    mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=activity_list.csv'})

# API: Outputs JSON of recent activity across all projects
@blueprint.route('/project/activity.json')
def projects_activity_json():
    limit = request.args.get('limit') or 10
    recent = Activity.query.order_by(Activity.id.desc()).limit(limit).all()
    return jsonify(activities=[a.data for a in recent])

# API: Outputs JSON of recent posts (a type of activity) across projects
@blueprint.route('/project/posts.json')
def projects_posts_json():
    limit = request.args.get('limit') or 10
    recent = Activity.query.filter(Activity.action=="post")
    recent = recent.order_by(Activity.id.desc())
    recent = recent.limit(limit).all()
    return jsonify(activities=[a.data for a in recent])

# API: Outputs JSON of recent activity of a project
@blueprint.route('/project/<int:project_id>/activity.json')
def project_activity_json(project_id):
    limit = request.args.get('limit') or 10
    project = Project.query.filter_by(id=project_id).first_or_404()
    query = Activity.query.filter_by(project_id=project.id).order_by(Activity.id.desc()).limit(limit).all()
    activities = [a.data for a in query]
    return jsonify(project=project.data, activities=activities)

# API: Outputs JSON info for a specific project
@blueprint.route('/project/<int:project_id>/info.json')
def project_info_json(project_id):
    project = Project.query.filter_by(id=project_id).first_or_404()
    activities = []
    for user in project.team():
        activities.append({
            'id': user.id,
            'name': user.username,
            'link': user.webpage_url
        })

    data = {
        'project': project.data,
        'phase': project.phase,
        'pitch': project.webembed,
        'is_webembed': project.is_webembed,
        'event': project.event.data,
        'creator': {
            'id': project.user.id,
            'username': project.user.username
        },
        'team': activities
    }

    return jsonify(data)

# ------ SEARCH ---------

def expand_project_urls(projects):
    for p in projects:
        p['event_url'] = request.host_url + p['event_url']
        p['url'] = request.host_url + p['url']
    return projects

# API: Full text search projects
@blueprint.route('/project/search.json')
def project_search_json():
    q = request.args.get('q')
    if q is None or len(q) < 3: return jsonify(projects=[])
    limit = request.args.get('limit') or 10
    q = "%%%s%%" % q
    projects = Project.query.filter(or_(
        Project.name.like(q),
        Project.summary.like(q),
        Project.longtext.like(q),
        Project.autotext.like(q),
    )).limit(limit).all()
    projects = expand_project_urls([p.data for p in projects])
    return jsonify(projects=projects)

# ------ UPDATE ---------

# API: Pushes data into a project
@blueprint.route('/project/push.json', methods=["PUT", "POST"])
def project_push_json():
    data = request.get_json(force=True)
    if not 'key' in data or data['key'] != current_app.config['DRIBDAT_APIKEY']:
        return jsonify(error='Invalid key')
    project = Project.query.filter_by(hashtag=data['hashtag']).first()
    if not project:
        project = Project()
        project.user_id = 1
        project.progress = 0
        # project.autotext_url = "#bot"
        # project.is_autoupdate = True
        project.event = Event.query.filter_by(is_current=True).first()
    elif project.user_id != 1 or project.is_hidden:
        return jsonify(error='Access denied')
    project.hashtag = data['hashtag']
    if 'name' in data and len(data['name']) > 0:
        project.name = data['name']
    else:
        project.name = project.hashtag.replace('-', ' ')
    if 'summary' in data and len(data['summary']) > 0:
        project.summary = data['summary']
    hasLongtext = 'longtext' in data and len(data['longtext']) > 0
    if hasLongtext:
        project.longtext = data['longtext']
    if 'autotext_url' in data and data['autotext_url'].startswith('http'):
        project.autotext_url = data['autotext_url']
        if not project.source_url or project.source_url == '':
            project.source_url = data['autotext_url']
    if 'levelup' in data and 0 < project.progress + data['levelup'] * 10 < 50: # MAX progress
        project.progress = project.progress + data['levelup'] * 10
    # return jsonify(data=data)
    if project.autotext_url is not None and not hasLongtext:
        # Now try to autosync
        data = GetProjectData(project.autotext_url)
        if 'name' in data:
            if len(data['name']) > 0:
                project.name = data['name'][0:80]
            if 'summary' in data and len(data['summary']) > 0:
                project.summary = data['summary'][0:120]
            if 'description' in data and len(data['description']) > 0:
                project.longtext = data['description']
            if 'homepage_url' in data and len(data['homepage_url']) > 0:
                project.webpage_url = data['homepage_url'][0:2048]
            if 'source_url' in data and len(data['source_url']) > 0:
                project.source_url = data['source_url'][0:255]
            if 'image_url' in data and len(data['image_url']) > 0:
                project.image_url = data['image_url'][0:255]
    project.update()
    db.session.add(project)
    db.session.commit()
    return jsonify(success='Updated', project=project.data)

# ------ FRONTEND -------

# API routine used to help sync project data
@blueprint.route('/project/autofill', methods=['GET', 'POST'])
@login_required
def project_autofill():
    url = request.args.get('url')
    data = GetProjectData(url)
    return jsonify(data)


import boto3, botocore
from botocore.exceptions import ClientError
from botocore.client import Config

# API: Enables uploading images into a project
@blueprint.route('/project/uploader', methods=["POST"])
@login_required
def project_uploader():
    if not current_app.config['S3_KEY']: return ''
    if len(request.files) == 0: return 'No files selected'
    img = request.files['file']
    if not img or img.filename == '': return 'No filename'
    ext = img.filename.split('.')[-1].lower()
    if not ext in ['png','jpg','jpeg','gif']: return 'Invalid format'
    filename = random_password(24) + '.' + ext
    # with tempfile.TemporaryDirectory() as tmpdir:
        # img.save(path.join(tmpdir, filename))
    s3_filepath = '/'.join([current_app.config['S3_FOLDER'], filename])
    print('Uploading to %s' % s3_filepath)
    s3_obj = boto3.client('s3',
      aws_access_key_id=current_app.config['S3_KEY'],
      aws_secret_access_key=current_app.config['S3_SECRET'],
      config=botocore.client.Config(region_name=current_app.config['S3_REGION']))
    s3_obj.upload_fileobj(
        img,
        current_app.config['S3_BUCKET'],
        s3_filepath,
        ExtraArgs={ 'ContentType': img.content_type, 'ACL': 'public-read' }
      )
    return '/'.join([current_app.config['S3_HTTPS'], s3_filepath])

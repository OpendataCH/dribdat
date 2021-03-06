# -*- coding: utf-8 -*-
"""Utilities for aggregating data
"""

from dribdat.user.models import Activity
from dribdat.database import db
from dribdat.apifetch import * # TBR

def GetProjectData(url):
    data = None
    if url.find('//gitlab.com') > 0:
        apiurl = re.sub(r'https?://gitlab\.com/', '', url).strip('/')
        if apiurl == url: return {}
        return FetchGitlabProject(apiurl)

    elif url.find('//github.com') > 0:
        apiurl = re.sub(r'https?://github\.com/', '', url).strip('/')
        if apiurl == url: return {}
        return FetchGithubProject(apiurl)

    elif url.find('//bitbucket.org') > 0:
        apiurl = re.sub(r'https?://bitbucket\.org', '', url).strip('/')
        if apiurl == url: return {}
        return FetchBitbucketProject(apiurl)

    # The fun begins
    elif url.find('/datapackage.json') > 0:
        return FetchDataProject(url)

    # Now we're really rock'n'rollin'
    else:
        return FetchWebProject(url)

def SyncProjectData(project, data):
    # Project name should *not* be updated
    # Always update "autotext" field
    if 'description' in data and data['description']:
        project.autotext = data['description']
    # Update following fields only if blank
    if 'summary' in data and data['summary']:
        if not project.summary or not project.summary.strip():
            project.summary = data['summary']
    if 'homepage_url' in data and data['homepage_url'] and not project.webpage_url:
        project.webpage_url = data['homepage_url']
    if 'contact_url' in data and data['contact_url'] and not project.contact_url:
        project.contact_url = data['contact_url']
    if 'source_url' in data and data['source_url'] and not project.source_url:
        project.source_url = data['source_url']
    if 'image_url' in data and data['image_url'] and not project.image_url:
        project.image_url = data['image_url']
    project.update()
    db.session.add(project)
    db.session.commit()

def IsProjectStarred(project, current_user):
    if not current_user or current_user.is_anonymous or not current_user.is_authenticated:
        return False
    return Activity.query.filter_by(
        name='star',
        project_id=project.id,
        user_id=current_user.id
    ).count() > 0

def GetEventUsers(event):
    if not event.projects: return None
    users = []
    userlist = []
    for p in event.projects:
        for u in p.team():
            if u.active and not u.id in userlist:
                userlist.append(u.id)
                users.append(u)
    return sorted(users, key=lambda x: x.username)

def ProjectActivity(project, of_type, current_user, action=None, comments=None):
    activity = Activity(
        name=of_type,
        project_id=project.id,
        user_id=current_user.id,
        action=action
    )
    if comments is not None and len(comments) > 3:
        activity.content=comments
    score = 0
    if project.score is None: project.score = 0
    allstars = Activity.query.filter_by(
        name='star',
        project_id=project.id,
        user_id=current_user.id
    )
    if of_type == 'star':
        score = 2
        if allstars.count() > 0:
            return # One star per user
    elif of_type == 'unstar':
        score = 2
        if allstars.count() > 0:
            allstars[0].delete()
        #if current_user.is_admin:
        #    score = 10
        project.score = project.score - score
        project.save()
        return
    # Admin stars give projects special awards
    #if of_type == 'star' and current_user.is_admin:
    #    score = 10
    project.score = project.score + score
    project.save()
    db.session.add(activity)
    db.session.commit()

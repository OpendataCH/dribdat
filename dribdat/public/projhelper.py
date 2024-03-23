# -*- coding: utf-8 -*-
"""Helper functions for editing projects."""
from flask import (
    request, render_template, flash, url_for, redirect
)
from flask_login import current_user
from urllib.parse import quote, quote_plus
from datetime import datetime, timedelta
from dribdat.user.models import Event, Project
from dribdat.public.forms import (
    ProjectForm, ProjectDetailForm,
)
from dribdat.aggregation import (
    ProjectActivity, IsProjectStarred,
)
from dribdat.user import (
    validateProjectData, isUserActive,
)
from dribdat.database import db
from dribdat.extensions import cache


def current_event():
    """Just get current event."""
    return Event.current()


def check_update(obj, minutes=5):
    """Has the object been updated in the last minutes."""
    td = datetime.now() - obj.updated_at
    return td < timedelta(minutes=minutes)


def resources_by_stage(progress, resource_event=False):
    """Get all projects which are published in a resource-type event."""
    if resource_event:
        # No need to make suggestions in a Resource event
        return []
    project_list = []
    resource_events = [e.id for e in Event.query.filter_by(
        lock_resources=True, is_hidden=False).all()]
    for eid in resource_events:
        projects = Project.query.filter_by(
            event_id=eid, is_hidden=False, progress=progress)
        project_list.extend([p.data for p in projects.all()])
    return project_list


def templates_from_event(resource_event=False):
    """Get all projects which are published in a resource-type event."""
    if resource_event:
        # No need to make suggestions in a Resource event
        return []
    project_list = []
    template_events = [e.id for e in Event.query.filter_by(
        lock_templates=True).all()]
    for eid in template_events:
        projects = Project.query.filter_by(
            event_id=eid, is_hidden=False)
        project_list.extend([p.data for p in projects.all()])
    return project_list


def project_edit_action(project_id, detail_view=False):
    """Project editing handler."""
    project = Project.query.filter_by(id=project_id).first_or_404()
    starred = IsProjectStarred(project, current_user)

    allow_edit = starred or project.event.lock_resources \
        or (isUserActive(current_user) and current_user.is_admin)
    if not allow_edit:
        flash('You do not have access to edit this project.', 'warning')
        return project_action(project_id, None)

    allow_sync = project.is_autoupdateable and check_update(project)

    # Basic view
    if not detail_view:
        form = ProjectForm(obj=project, next=request.args.get('next'))

    # Detail view
    else:
        form = ProjectDetailForm(obj=project, next=request.args.get('next'))

        # Populate categories
        form.category_id.choices = [(c.id, c.name)
                                    for c in project.categories_all()]
        if len(form.category_id.choices) > 0:
            form.category_id.choices.insert(0, (-1, ''))
        else:
            del form.category_id

    # Continue with form validation
    if form.is_submitted() and form.validate():

        # Check for minor edit toggle
        if form.is_minoredit:
            is_minoredit = form.is_minoredit.data
            del form.is_minoredit
        else:
            is_minoredit = False
        
        del form.id
        form.populate_obj(project)
        project.update_now()
        db.session.add(project)
        db.session.commit()
        cache.clear()

        # Create an optional post update
        if 'note' in form and form.note.data:
            project_action(project_id, 'update',
                           action='post', text=form.note.data)
    
        # Save a log entry (unless minor) and notify the user
        if not is_minoredit:
            project_action(project_id, 'update', False)
            flash('Project updated.', 'success')
        else:
            flash('Saved changes.', 'success')

        if allow_sync:
            return redirect(url_for(
                'project.project_autoupdate', project_id=project.id))
        return redirect(url_for(
            'project.project_view', project_id=project.id))

    return render_template(
        'public/projectedit.html', detail_view=detail_view,
        current_event=project.event, project=project, form=form,
        active="projects"
    )


def project_action(project_id, of_type=None, as_view=True, then_redirect=False,
                   action=None, text=None, for_user=current_user):
    """Mother of all projects."""
    project = Project.query.filter_by(id=project_id).first_or_404()
    event = project.event
    if of_type is not None:
        ProjectActivity(project, of_type, for_user, action, text)
    if not as_view:
        return True
    if then_redirect:
        return redirect(url_for('project.project_view', project_id=project.id))

    # The next line seems rather inefficient
    starred = IsProjectStarred(project, for_user)
    # Figure out permissions (hackybehack!)
    allow_edit = not current_user.is_anonymous and current_user.is_admin
    lock_editing = event.lock_editing
    allow_post = starred and not event.lock_resources
    allow_edit = allow_edit or event.lock_resources
    allow_edit = (starred or allow_edit) and not lock_editing

    # Check type of project
    if event.lock_resources:
        project_dribs = project_badge = []
        project_team = None
        missing_roles = None
    else:
        # Collect dribs and badges
        project_dribs = project.all_dribs()
        project_badge = [s for s in project_dribs if s['name'] == 'boost']
        # Obtain list of team members (performance!)
        project_team = project.get_team()
        # Suggest missing team roles
        if allow_post:
            missing_roles = project.get_missing_roles()
        else:
            missing_roles = None

    # Select an image for the META tags
    if project.image_url:
        project_image_url = project.image_url
    elif event.logo_url:
        project_image_url = event.logo_url
    else:
        project_image_url = url_for(
            'static', filename='img/badge-black.png', _external=True)

    # Generate social links
    share = {
        'text': quote(" ".join([
            project.hashtag or project.name,
            event.hashtags or '#dribdat']).strip()),
        'url': quote_plus(request.url)
    }

    # Get navigation
    go_nav = navigate_around_project(project)

    # Send a warning for hidden projects
    if project.is_hidden:
        flash('This project is hidden, and needs moderation from an organizer.', 'warning')
    # Send a warning for unapproved challenges
    if project.progress is not None and project.progress < 0:
        flash('This challenge is awaiting approval from an organizer.', 'warning')

    # Dump all that data into a template
    return render_template(
        'public/project.html', current_event=event, project=project,
        project_starred=starred, project_team=project_team,
        project_badge=project_badge, project_dribs=project_dribs,
        project_image_url=project_image_url, go_nav=go_nav,
        allow_edit=allow_edit, allow_post=allow_post,
        lock_editing=lock_editing, missing_roles=missing_roles,
        share=share, active="projects"
    )


def revert_project_by_activity(project, activity):
    """Revert Project to a previous version based on an Activity."""
    if not activity.project_version:
        return None, 'Could not revert: data not available.'
    revert_to = activity.project_version
    if not revert_to > 0:
        return None, 'Could not revert: invalid version.'
    # Apply revert
    project.versions[revert_to].revert()
    return revert_to, 'Project data reverted to version %d.' % revert_to


def navigate_around_project(project, as_challenge=False):
    """Returns previous and next projects in the default order."""
    go_nav = {}
    # Sort visible projects by identity (if used), or alphabetically
    projects = Project.query \
        .filter_by(event_id=project.event_id, is_hidden=False) \
        .order_by(Project.ident, Project.name)
        # The above must match views->event
    p_prev = p_next = p_found = None
    for p in projects:
        if p_found:
            p_next = p
            break
        elif p.id == project.id:
            p_found = True
        else:
            p_prev = p
    if p_prev:
        go_nav['prev'] = p_prev.data
        go_nav['prev']['url'] = '/' + p_prev.url
        if as_challenge:
            go_nav['prev']['url'] = '/' + p_prev.url + '/challenge'
    if p_next:
        go_nav['next'] = p_next.data
        go_nav['next']['url'] = '/' + p_next.url
        if as_challenge:
            go_nav['next']['url'] = '/' + p_next.url + '/challenge'
    elif not p_prev:
        return None
    return go_nav
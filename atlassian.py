# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from urllib.parse import urlparse

from errbot import BotPlugin, botcmd, webhook
from errbot.templating import tenv
import errbot.backends.base

from err_routes import RouteMixin

log = logging.getLogger(name='errbot.plugins.atlassian')

ATLASSIAN_EVENTS = [
    'connect_addon_disabled',
    'connect_addon_enabled',
    'jira:issue_created',
    'jira:issue_deleted',
    'jira:issue_updated',
    'jira:worklog_updated',
    'jira:version_created',
    'jira:version_deleted',
    'jira:version_merged',
    'jira:version_updated',
    'jira:version_moved',
    'jira:version_released',
    'jira:version_unreleased',
    'project_created',
    'project_updated',
    'project_deleted',
    'user_created',
    'user_deleted',
    'user_updated',
    'option_voting_changed',
    'option_watching_changed',
    'option_unassigned_issues_changed',
    'option_subtasks_changed',
    'option_attachments_changed',
    'option_issuelinks_changed',
    'option_timetracking_changed',
    'attachment_created',
    'attachment_removed',
    'attachment_restored',
    'attachment_trashed',
    'attachment_updated',
    'attachment_viewed',
    'blog_created',
    'blog_removed',
    'blog_restored',
    'blog_trashed',
    'blog_updated',
    'blog_viewed',
    'blueprint_page_created',
    'comment_created',
    'comment_removed',
    'comment_updated',
    'connect_addon_disabled',
    'connect_addon_enabled',
    'content_permissions_updated',
    'group_created',
    'group_removed',
    'label_added',
    'label_created',
    'label_deleted',
    'label_removed',
    'login',
    'login_failed',
    'logout',
    'page_children_reordered',
    'page_created',
    'page_moved',
    'page_removed',
    'page_restored',
    'page_trashed',
    'page_updated',
    'page_viewed',
    'search_performed',
    'space_created',
    'space_logo_updated',
    'space_permissions_updated',
    'space_removed',
    'space_updated',
    'user_created',
    'user_deactivated',
    'user_followed',
    'user_reactivated',
    'user_removed',
]


class Atlassian(RouteMixin, BotPlugin):

    min_err_version = '2.1.0'
    README_URL = 'https://github.com/mayflower/err-atlassian/blob/master/README.rst'
    DEFAULT_EVENTS = AVAILABLE_EVENTS = ATLASSIAN_EVENTS
    HELP_MSG = ('Please see the output of `!atlassian help` for usage '
                'and configuration instructions.')

    def __init__(self, *args, **kwargs):
        super(Atlassian, self).__init__(*args, **kwargs)
        self.concise_output = self._bot.bot_config.get('ATLASSIAN_CONCISE_MESSAGES', False)

    def get_configuration_template(self):
        return self.HELP_MSG

    def check_configuration(self, configuration):
        pass

    ###########################################################
    # Commands for the user to get, set or clear configuration.
    ###########################################################

    @botcmd
    def atlassian(self, *args):
        """Atlassian root command, return usage information."""
        return self.routes_root_help(*args)

    @botcmd
    def atlassian_help(self, *args):
        """Output help."""
        return self.routes_help(*args)

    @botcmd(admin_only=True)
    def atlassian_config(self, *args):
        """Returns the current configuration of the plugin routes"""
        return self.routes_config(*args)

    @botcmd(admin_only=True)
    def atlassian_reset(self, *args):
        """Nuke the complete configuration."""
        return self.routes_reset(*args)

    @botcmd(split_args_with=None)
    def atlassian_defaults(self, message, args):
        """Get or set what events are relayed by default for new routes."""
        return self.routes_defaults(message, args)

    @botcmd(split_args_with=None)
    def atlassian_route(self, message, args):
        """Map a project to a chatroom, essentially creating a route.

        This takes two or three arguments: author/project, a chatroom and
        optionally a list of events.

        If you do not specify a list of events the route will default to
        receiving the events configured as 'default_events'.
        """
        self.routes_add_route(message, args)

    @botcmd(split_args_with=None)
    def atlassian_routes(self, message, args):
        self.routes_list_routes(message, args)

    @botcmd(split_args_with=None)
    def atlassian_remove(self, message, args):
        """Remove a route or a project.

        If only one argument is passed all configuration for that project
        is removed.

        When two arguments are passed that specific route is removed. If this
        was the last route any remaining configuration for the project is
        removed too. With only one route remaining this essentially achieves
        the same result as calling this with only the project as argument.
        """
        self.routes_remove(message, args)

    @botcmd(split_args_with=None)
    def atlassian_global(self, message, args):
        """Set a global route"""
        return self.routes_global(message, args)

    @webhook(r'/atlassian', methods=('POST',), raw=True)
    def receive(self, request):
        """Handle the incoming payload.

        Here be dragons.

        Validate the payload as best as we can and then delegate the creation
        of a sensible message to a function specific to this event. If no such
        function exists, use a generic message function.

        Once we have a message, route it to the appropriate channels.
        """
        self.routes_receive(request)

    def join_and_send(self, room_name, message):
        try:
            room = self.query_room(room_name)
            room.join(username=self._bot.bot_config.CHATROOM_FN)
        except errbot.backends.base.RoomError as e:
            # default to simple behavior if rooms unsupported
            room = self.build_identifier(room_name)
            self.log.info(e)
        if isinstance(message, dict):
            if not hasattr(self._bot, 'telegram'):
                self.send_card(
                    to=room,
                    **message
                )
            else:
                template_name = 'concise' if self.concise_output else 'simple_card'
                params = message if self.concise_output else {'card': message}
                self.send_templated(identifier=room, template_name=template_name,
                                    template_parameters=params)
        else:
            self.send(room, message)

    def is_global_event(self, event_type, project, body):
        return event_type in ['user_deleted']

    @staticmethod
    def validate_incoming(request):
        """Validate the incoming request:
          Check if the payload decodes to something we expect
        """
        try:
            body = request.json
        except ValueError:
            log.debug('ValueError while decoding JSON')
            return False

        if not isinstance(body, dict):
            log.debug('body is not a dict')
            return False

        return True

    # handlers section
    @staticmethod
    def msg_generic(body, project, event_type):
        return tenv().get_template('generic.html').render(locals().copy())

    @staticmethod
    def msg_issue_generic(body, project, event_type=None):
        summary = body['issue']['fields']['summary']
        url_parts = urlparse(body['issue']['self'])
        base_url = '{}://{}'.format(url_parts.scheme, url_parts.hostname)
        user = body['user']['displayName']
        key = body['issue']['key']
        if 'changelog' in body:
            url = '{}/browse/{}'.format(base_url, key)
            changes = []
            for item in body['changelog']['items']:
                field = item['field'][0].upper() + item['field'][1:]
                changes.append((field, '{} → {}'.format(item['fromString'], item['toString'])))

            return {
                'summary': '[jira] {} edited issue {}'.format(user, key),
                'title': '{} - {}'.format(key, summary),
                'link': url,
                'fields': changes
            }

        if 'comment' in body:
            url = ('{base_url}/browse/{key}?focusedCommentId={commentId}'
                   '&page=com.atlassian.jira.plugin.system.issuetabpanels'
                   ':comment-tabpanel#comment-{commentId}').format(
                base_url=base_url,
                key=key,
                commentId=body['comment']['id']
            )
            action = 'created' if event_type == 'issue_commented' else 'edited'

            return {
                'summary': '[jira] {} {} a comment on {}'.format(user, action, key),
                'title': '{} - {}'.format(key, summary),
                'link': url,
                'body': body['comment']['body']
            }

    def msg_jira_issue_updated(self, body, project):
        if not self.concise_output:
            return self.msg_issue_generic(body, project, body['issue_event_type_name'])

        if 'changelog' in body:
            status_change = next((e.get('field') == 'status' for
                                  e in body['changelog']['items']), None)
            if status_change in ['Resolved', 'In Progress', 'Closed', 'Reopened']:
                user = body['user']['displayName']
                key = body['issue']['key']
                url = self.get_url(body, key)
                # send only issue status change
                return dict(user=user, issue=key, url=url, action=status_change.lower())

    def get_url(self, body, key):
        url_parts = urlparse(body['issue']['self'])
        base_url = '{}://{}'.format(url_parts.scheme, url_parts.hostname)
        url = '{}/browse/{}'.format(base_url, key)
        return url

    def msg_jira_issue_created(self, body, project):
        key = body['issue']['key']
        url = self.get_url(body, key)
        user = body['user']['displayName']
        summary = body['issue']['fields']['summary']
        description = body['issue']['fields']['description']

        if self.concise_output:
            return dict(user=user, issue=key, url=url, action='created')

        return {
            'summary': '[jira] {} created issue {}'.format(user, key),
            'title': '{} - {}'.format(key, summary),
            'link': url,
            'body': description
        }

    @staticmethod
    def msg_jira_issue_deleted(body, project):
        user = body['user']['displayName']
        key = body['issue']['key']
        summary = body['issue']['fields']['summary']

        return '[jira] {} deleted an issue {} - {}'.format(user, key, summary)

    @staticmethod
    def msg_issue_comment_deleted(body, project):
        url_parts = urlparse(body['issue']['self'])
        base_url = '{}://{}'.format(url_parts.scheme, url_parts.hostname)
        user = body['user']['displayName']
        key = body['issue']['key']
        url = '{}/browse/{}'.format(base_url, key)

        return '[jira] {} deleted a comment on {} ({})'.format(user, key, url)

    @staticmethod
    def msg_user_deleted(body, project):
        user = body['user']['name']

        return '[jira] User {} was deleted'.format(user)

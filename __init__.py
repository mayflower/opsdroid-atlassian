# -*- coding: utf-8 -*-

import logging
import json
from urllib.parse import urlparse

from aiohttp.web import Request, Response

from opsdroid.events import Message
from opsdroid.matchers import match_regex, match_webhook
from opsdroid.skill import Skill

# from jira import JIRA, JIRAError
# from .jira_oauth import JiraOauth

log = logging.getLogger(name="errbot.plugins.atlassian")

GLOBAL_ROUTE = "atlassian_global_route"
DEFAULT_EVENTS = "atlassian_default_events"
ROUTES = "atlassian_routes"

ATLASSIAN_EVENTS = [
    "attachment_created",
    "attachment_removed",
    "attachment_restored",
    "attachment_trashed",
    "attachment_updated",
    "attachment_viewed",
    "blog_created",
    "blog_removed",
    "blog_restored",
    "blog_trashed",
    "blog_updated",
    "blog_viewed",
    "blueprint_page_created",
    "board_configuration_changed",
    "board_created",
    "board_deleted",
    "board_updated",
    "comment_created",
    "comment_deleted",
    "comment_removed",
    "comment_updated",
    "connect_addon_disabled",
    "connect_addon_enabled",
    "content_created",
    "content_restored",
    "content_trashed",
    "content_updated",
    "content_permissions_updated",
    "group_created",
    "group_removed",
    "issue_property_set",
    "issue_property_deleted" "issuelink_created",
    "issuelink_deleted",
    "jira:issue_created",
    "jira:issue_deleted",
    "jira:issue_updated",
    "jira:version_created",
    "jira:version_deleted",
    "jira:version_moved",
    "jira:version_released",
    "jira:version_unreleased",
    "jira:version_updated",
    "label_added",
    "label_created",
    "label_deleted",
    "label_removed",
    "login",
    "login_failed",
    "logout",
    "option_attachments_changed",
    "option_issuelinks_changed",
    "option_subtasks_changed",
    "option_timetracking_changed",
    "option_unassigned_issues_changed",
    "option_voting_changed",
    "option_watching_changed",
    "page_children_reordered",
    "page_created",
    "page_moved",
    "page_removed",
    "page_restored",
    "page_trashed",
    "page_updated",
    "page_viewed",
    "project_created",
    "project_deleted",
    "project_updated",
    "relation_created",
    "relation_deleted",
    "search_performed",
    "space_created",
    "space_logo_updated",
    "space_permissions_updated",
    "space_removed",
    "space_updated",
    "sprint_closed",
    "sprint_created",
    "sprint_deleted",
    "sprint_started",
    "sprint_updated",
    "theme_enabled",
    "user_created",
    "user_deactivated",
    "user_deleted",
    "user_followed",
    "user_reactivated",
    "user_removed",
    "user_updated",
    "worklog_created",
    "worklog_deleted",
    "worklog_updated",
]

GLOBAL_EVENTS = [
    "blog_created",
    "blog_removed",
    "project_created",
    "project_updated",
    "project_deleted",
    "user_created",
    "user_deleted",
    "user_updated",
    "option_voting_changed",
    "option_watching_changed",
    "option_unassigned_issues_changed",
    "option_subtasks_changed",
    "option_attachments_changed",
    "option_issuelinks_changed",
    "option_timetracking_changed",
    "space_created",
    "space_removed",
    "user_deactivated",
    "user_followed",
    "user_reactivated",
    "user_removed",
]

HELP_MSG = (
    "Please see the output of `!atlassian help` for usage "
    "and configuration instructions."
)

PROJECT_UNKNOWN = "The project {0} is unknown to me."
EVENT_UNKNOWN = "Unknown event {0}, skipping."

README = "https://github.com/mayflower/err-atlassian/blob/master/README.rst"


class JiraNeedsAuthorization(Exception):
    pass


class Atlassian(Skill):
    @match_regex(
        r"!atlassian defaults(?:\s+(?P<events>\S+))?", matching_condition="fullmatch"
    )
    async def atlassian_defaults(self, message):
        """Get or set what events are relayed by default for new routes."""
        events = message.entities.get("events", {}).get("value", "").split(",")

        if events:
            for event in events:
                if event not in ATLASSIAN_EVENTS:
                    await message.respond(EVENT_UNKNOWN.format(event))
                    return

            await self.opsdroid.memory.put(DEFAULT_EVENTS, events)
            await message.respond(
                "Done. Newly created routes will default to "
                "receiving: {0}.".format(" ".join(events))
            )
        else:
            events = await self.opsdroid.memory.get(DEFAULT_EVENTS)
            await message.respond(
                "Events routed by default: " "{0}.".format(" ".join(events))
            )

    @match_regex(
        r"!atlassian route (?P<project>\S+) (?P<room>\S+)(?:\s+(?P<events>\S+))?",
        matching_condition="fullmatch",
    )
    async def atlassian_route(self, message):
        """Map a project to a chatroom, essentially creating a route.

        This takes two or three arguments: author/project, a chatroom and
        optionally a list of events.

        If you do not specify a list of events the route will default to
        receiving the events configured as 'default_events'.
        """
        project = message.entities["project"]["value"]
        room = message.entities["room"]["value"]
        events = message.entities.get("events", {}).get("value")

        routes = await self.opsdroid.memory.get(ROUTES)
        routes = {} if routes is None else routes

        if events:
            events = events.split(",")
            for event in events:
                if event not in ATLASSIAN_EVENTS and event != "*":
                    await message.respond(EVENT_UNKNOWN.format(event))
                    events.remove(event)
        else:
            events = await self.opsdroid.memory.get(DEFAULT_EVENTS)
            if not events:
                events = ATLASSIAN_EVENTS

        project_routes = routes.get(project, {})
        project_routes[room] = events
        routes[project] = project_routes
        log.debug(f"project_routes configured {project_routes}")
        log.debug(f"routes configured {routes}")

        await self.opsdroid.memory.put(ROUTES, routes)

        await message.respond(
            "Done. Relaying messages from {0} to {1} for "
            "events: {2}".format(project, room, ",".join(events))
        )

    @match_regex(
        r"!atlassian routes(?:\s+(?P<project>\S+))?", matching_condition="fullmatch",
    )
    async def atlassian_routes(self, message):
        """Displays the routes for one, multiple or all projects."""
        routes = await self.opsdroid.memory.get(ROUTES)
        routes = {} if routes is None else routes

        project = message.entities.get("project", {}).get("value")
        if project:
            if routes.get(project):
                await message.respond(json.dumps(routes.get(project)))
            else:
                await message.respond(PROJECT_UNKNOWN.format(project))
        else:
            await message.respond(json.dumps(routes))

    @match_regex(
        r"!atlassian remove (?P<project>\S+)(?:\s+(?P<room>\S+))?",
        matching_condition="fullmatch",
    )
    async def atlassian_remove(self, message):
        routes = await self.opsdroid.memory.get(ROUTES)
        routes = {} if routes is None else routes

        project = message.entities["project"]["value"]
        room = message.entities.get("room", {}).get("value")
        if not room:
            if project in routes:
                del routes[project]
                await message.respond(f"Removed all configuration for {project}.")
        else:
            if project in routes and room in routes[project]:
                del routes[project][room]
                await message.respond(f"Removed route for {project} to {room}.")
                if not routes[project]:
                    del routes[project]

        await self.opsdroid.memory.put(ROUTES, routes)

    @match_regex(
        r"!atlassian global(?:\s+(?P<room>\S+))?", matching_condition="fullmatch"
    )
    async def atlassian_global(self, message):
        """Set a global route"""
        room = message.entities.get("room", {}).get("value")
        if not room:
            await self.opsdroid.memory.delete(GLOBAL_ROUTE)
            await message.respond("Removed global route.")
        else:
            await self.opsdroid.memory.put(GLOBAL_ROUTE, room)
            await message.respond(f"Set global route to {room}.")

    # def _handle_jira_auth(self, user):
    #     oauth = JiraOauth()
    #     link, state = oauth.request_token()
    #     self["oauth_request_{}".format(user)] = state

    #     return link

    # def _jira_req_auth(self, frm):
    #     link = self._handle_jira_auth(frm)
    #     text = "To use the errbot JIRA integration please give permission at: {}".format(
    #         link
    #     )
    #     self.send(self.build_identifier(frm), text)
    #     raise JiraNeedsAuthorization()

    # def _jira_client(self, message):
    #     frm = getattr(message.frm, "real_jid", message.frm.person)
    #     request_key = "oauth_request_{}".format(frm)
    #     access_key = "oauth_access_{}".format(frm)
    #     self.log.warn("FROM: %s", frm)
    #     if self.get(request_key):
    #         oauth = JiraOauth()
    #         state = self[request_key]
    #         try:
    #             self[access_key] = oauth.accepted(state)
    #         except KeyError:
    #             self._jira_req_auth(frm)
    #         del self[request_key]
    #     if not self.get(access_key):
    #         self._jira_req_auth(frm)
    #     token, secret = self[access_key]
    #     oauth_config = {
    #         "access_token": token,
    #         "access_token_secret": secret,
    #         "consumer_key": self.config["JIRA_OAUTH_KEY"],
    #         "key_cert": self.config["JIRA_OAUTH_PEM"],
    #     }

    #     return JIRA(self.config["JIRA_BASE_URL"], oauth=oauth_config)

    # @botcmd
    # def jira_auth(self, message, args):
    #     """Sends you the link to grant an OAuth token in JIRA"""
    #     if not message.is_direct:
    #         return "This has to be used in a direct message."
    #     return self._handle_jira_auth(message.frm.person)

    # @botcmd
    # def jira_forget(self, message, args):
    #     """Deletes your JIRA OAuth token"""
    #     if not message.is_direct:
    #         return "This has to be used in a direct message."
    #     if self.get("oauth_access_{}".format(message.frm.person)):
    #         del self["oauth_access_{}".format(message.frm.person)]
    #     if self.get("oauth_request_{}".format(message.frm.person)):
    #         del self["oauth_request_{}".format(message.frm.person)]
    #     return "Your OAuth token has been deleted."

    # @re_botcmd(pattern=r"\b[A-Z]+-[0-9]+\b", prefixed=False, matchall=True)
    # def jira_issue(self, message, matches):
    #     """Prints JIRA issue information if it recognizes an issue key"""
    #     if type(message.frm).__name__ == "SlackRoomBot":
    #         return
    #     try:
    #         client = self._jira_client(message)
    #         for match in matches:
    #             try:
    #                 issue = client.issue(match.group())
    #                 epic_link_name = None
    #                 if issue.fields.customfield_10680:
    #                     epic_link = client.issue(
    #                         issue.fields.customfield_10680
    #                     )  # FIXME
    #                     epic_link_name = epic_link.fields.customfield_10681
    #                 issue_card = {
    #                     "to": getattr(message.frm, "room", message.frm),
    #                     "summary": issue.fields.description,
    #                     "title": "{} - {}".format(issue.key, issue.fields.summary),
    #                     "link": "{}/browse/{}".format(
    #                         self.config["JIRA_BASE_URL"], issue.key
    #                     ),
    #                     "fields": [
    #                         (k, v)
    #                         for k, v in list(
    #                             {
    #                                 "Assignee": getattr(
    #                                     issue.fields.assignee, "displayName", None
    #                                 ),
    #                                 "Due Date": issue.fields.duedate,
    #                                 "Reporter": getattr(
    #                                     issue.fields.reporter, "displayName", None
    #                                 ),
    #                                 "Created": issue.fields.created,
    #                                 "Priority": issue.fields.priority.name,
    #                                 "Status": issue.fields.status.name,
    #                                 "Resolution": getattr(
    #                                     issue.fields.resolution, "name", None
    #                                 ),
    #                                 "Epic Link": epic_link_name,
    #                             }.items()
    #                         )
    #                         if v
    #                     ],
    #                 }
    #                 self.send_card(**issue_card)
    #             except JIRAError as err:
    #                 if err.status_code == 404:
    #                     yield "No Issue {} found".format(match.group())
    #     except JiraNeedsAuthorization:
    #         pass

    @match_webhook("atlassian")
    async def receive(self, request: Request):
        """Handle the incoming payload.

        Here be dragons.

        Validate the payload as best as we can and then delegate the creation
        of a sensible message to a function specific to this event. If no such
        function exists, use a generic message function.

        Once we have a message, route it to the appropriate channels.
        """

        body = await request.json()
        event_type = body["webhookEvent"]

        project = body["issue"]["fields"]["project"]["key"] if "issue" in body else None
        global_event = event_type in GLOBAL_EVENTS

        routes = await self.opsdroid.memory.get(ROUTES)
        routes = {} if routes is None else routes
        if not routes.get(project) and not global_event:
            # Not a project we know so accept the payload, return 200 but
            # discard the message
            log.info(
                f"Event {event_type} received for {project} but no such project "
                "is configured."
            )
            return Response(status=204)

        message = self.dispatch_event(body, project, event_type)

        # - if we have a message and is it not empty or None
        # - get all rooms for the project we received the event for
        # - check if we should deliver this event
        # - join the room (this won't do anything if we're already joined)
        # - send the message
        if message:
            for room_name in routes.get(project, {}):
                events = routes[project][room_name]
                if event_type in events or "*" in events:
                    await self.opsdroid.send(Message(message, target=room_name))
            global_route = await self.opsdroid.memory.get(GLOBAL_ROUTE)
            if global_event and global_route:
                await self.opsdroid.send(Message(message, target=global_route))

        return Response(status=204)

    def dispatch_event(self, body, project, event_type, generic_fn=None):
        """
        Dispatch the message. Check explicitly with hasattr first. When
        using a try/catch with AttributeError errors in the
        message_function which result in an AttributeError would cause
        us to call msg_generic, which is not what we want.
        """
        if generic_fn is None:
            generic_fn = self.msg_generic

        message_function = "msg_{0}".format(event_type.replace(":", "_"))
        if hasattr(self, message_function):
            message = getattr(self, message_function)(body, project)
        else:
            message = generic_fn(body, project, event_type)
        return message

    @staticmethod
    def msg_generic(body, project, event_type):
        return f"{event_type} on {project}: {body}"

    @staticmethod
    def msg_issue_generic(body, project, event_type=None):
        summary = body["issue"]["fields"]["summary"]
        url_parts = urlparse(body["issue"]["self"])
        base_url = "{}://{}".format(url_parts.scheme, url_parts.hostname)
        user = body["user"]["displayName"]
        key = body["issue"]["key"]
        if "changelog" in body:
            url = "{}/browse/{}".format(base_url, key)
            changes = []
            comment = body.get("comment", {}).get("body","")
            for item in body["changelog"]["items"]:
                field = item["field"][0].upper() + item["field"][1:]
                from_, to = item["fromString"], item["toString"]
                changes.append(f"{field}: {from_} → {to}")

            return f"""[JIRA] {user} edited issue <a href="{url}">{key}</a>
                       <br>
                       <b>{summary}</b>
                       <br>""" + "<br>".join(
                changes
            ) + (f"<pre>{comment}</pre>" if comment != "" else "")

        if "comment" in body:
            commentId = body["comment"]["id"]
            url = f"{base_url}/browse/{key}?focusedCommentId={commentId}&page=com.atlassian.jira.plugin.system.issuetabpanels:comment-tabpanel#comment-{commentId}"
            action = "created" if event_type == "issue_commented" else "edited"

            return (
                f"""[JIRA] {user} {action} a comment on <a href="{url}">{key}</a>
                    <br>
                    <b>{summary}</b>
                    <br>""" "<pre>" + body["comment"]["body"] + "</pre>"
            )

    def msg_jira_issue_updated(self, body, project):
        return self.dispatch_event(
            body, project, body["issue_event_type_name"], self.msg_issue_generic
        )

    @staticmethod
    def msg_jira_issue_created(body, project):
        url_parts = urlparse(body["issue"]["self"])
        base_url = "{}://{}".format(url_parts.scheme, url_parts.hostname)
        key = body["issue"]["key"]
        url = "{}/browse/{}".format(base_url, key)
        user = body["user"]["displayName"]
        summary = body["issue"]["fields"]["summary"]
        description = body["issue"]["fields"]["description"]

        return f"""[JIRA] {user} created issue <a href="{url}">{key}</a>
                   <br>
                   <b>{summary}<b>
                   <pre>{description}</pre>"""

    @staticmethod
    def msg_jira_issue_deleted(body, project):
        user = body["user"]["displayName"]
        key = body["issue"]["key"]
        summary = body["issue"]["fields"]["summary"]

        return f"""[JIRA] {user} deleted issue {key}
                   <br>
                   <b>{summary}<b>"""

    @staticmethod
    def msg_issue_comment_deleted(body, project):
        url_parts = urlparse(body["issue"]["self"])
        base_url = "{}://{}".format(url_parts.scheme, url_parts.hostname)
        user = body["user"]["displayName"]
        key = body["issue"]["key"]
        url = "{}/browse/{}".format(base_url, key)

        return f'[JIRA] {user} deleted a comment on <a href="{url}">{key}</a>'

    @staticmethod
    def msg_user_deleted(body, project):
        user = body["user"]["name"]

        return f"[JIRA] User {user} was deleted"

    @staticmethod
    def msg_user_created(body, project):
        user = body["user"]["name"]

        return f"[JIRA] User {user} was created"

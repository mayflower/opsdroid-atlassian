import json

from errbot.rendering import md_escape
from bottle import abort, response


class RouteMixin(object):
    """
    This mixin can be added to any Plugin to add webhook routes functionality.

    This means that incoming event handlers are looked up according
    to pre-configured set of routes, prefixed by a "projects" namespace.
    """
    DEFAULT_EVENTS = AVAILABLE_EVENTS = []
    README_URL = None  # set me to url for additional user help
    PROJECT_UNKNOWN = 'The project {0} is unknown to me.'
    EVENT_UNKNOWN = 'Unknown event {0}, skipping.'

    def __init__(self, *args, **kwargs):
        super(RouteMixin, self).__init__(*args, **kwargs)
        self.DEFAULT_ROUTES_CONFIG = {'default_events': self.DEFAULT_EVENTS, 'projects': {}, }

    def configure(self, configuration):
        if configuration is not None:
            config = configuration
        else:
            config = self.DEFAULT_ROUTES_CONFIG
        super(RouteMixin, self).configure(config)

    #################################################################
    # Convenience methods to get, check or set configuration options.
    #################################################################

    def clear_project(self, project):
        """Completely remove a project's configuration."""
        if self.has_project(project):
            self.config['projects'].pop(project)
            self.save_config()

    def clear_route(self, project, room):
        """Remove a route from a project."""
        if self.has_route(project, room):
            self.config['projects'][project]['routes'].pop(room)
            self.save_config()

    def has_project(self, project):
        """Check if the project is known."""
        if self.get_project(project) is None:
            return False
        else:
            return True

    def has_route(self, project, room):
        """Check if we have a route for this project to that room."""
        if self.get_route(project, room) is None:
            return False
        else:
            return True

    def get_defaults(self):
        """Return the default events that get relayed."""
        return self.config['default_events']

    def get_events(self, project, room):
        """Return all the events being relayed for this combination of
        project and room, aka a route.
        """
        return self.config['projects'].get(
            project, {}).get('routes', {}).get(
                room, {}).get('events')

    def get_project(self, project):
        """Return the project's configuration or None."""
        return self.config['projects'].get(project)

    def get_projects(self):
        """Return a list of all projects we have configured."""
        return self.config['projects'].keys()

    def get_route(self, project, room):
        """Return the configuration of this route."""
        return self.config['projects'].get(
            project, {}).get('routes', {}).get(room)

    def get_routes(self, project):
        """Fetch the routes for a project.
        Always check if the project exists before calling this.
        """
        return self.config['projects'].get(
            project, {}).get('routes', {}).keys()

    def set_defaults(self, defaults):
        """Set which events are relayed by default."""
        self.config['default_events'] = defaults
        self.save_config()

    def set_events(self, project, room, events):
        """Set the events to be relayed for this combination of project
        and room."""
        self.config['projects'][project]['routes'][room]['events'] = events
        self.save_config()

    def set_route(self, project, room):
        """Create a configuration entry for this route.

        If the project is unknown to us, add the project first.
        """
        if self.get_project(project) is None:
            self.config['projects'][project] = {'routes': {}}
        self.config['projects'][project]['routes'][room] = {}
        self.save_config()

    def save_config(self):
        """Save the current configuration.

        This method takes care of saving the configuration since we can't
        use !config Atlassian <configuration blob> to configure this
        plugin.
        """
        self._bot.plugin_manager.set_plugin_configuration('Atlassian',
                                                          self.config)

    def show_project_config(self, project):
        """Builds up a complete list of rooms and events for a project."""
        if self.has_project(project):
            message = ['Routing {0} to:'.format(project)]
            for room in self.get_routes(project):
                message.append(' • {0} for events: {1}'.format(
                    room, md_escape(' '.join(self.get_events(project, room)))))
            return '\n'.join(message)
        else:
            return PROJECT_UNKNOWN.format(project)

    ###########################################################
    # Commands for the user to get, set or clear configuration.
    ###########################################################

    def routes_root_help(self, *args):
        """Routes root command, return usage information."""
        return self.routes_help()

    def routes_help(self, *args):
        """Output help."""
        message = []
        message.append('This plugin has multiple commands: ')
        message.append(' • config: to display the full configuration of '
                       'this plugin (not human friendly)')
        message.append(md_escape(
            ' • route <project> <room>: to relay messages from '
            '<project> to <room> for events '
            '{0}'.format(' '.join(self.get_defaults()))))
        message.append(' • route <project> <room> <events>: to relay '
                       'messages from <project> to <room> for <events>')
        message.append(' • routes <project>: show routes for this project')
        message.append(' • routes: to display all routes')
        message.append(' • global route <room>: to set a route for global events')
        message.append(' • defaults <events>: to configure the events we '
                       'should forward by default')
        message.append(' • defaults: to show the events to be forwarded '
                       'by default')
        if self.README_URL:
            message.append('Please see {0} for more information.'.format(self.README_URL))
        return '\n'.join(message)

    def routes_config(self, *args):
        """Returns the current configuration of the plugin."""
        # pprint can't deal with nested dicts, json.dumps is aces.
        return json.dumps(self.config, indent=4, sort_keys=True)

    def routes_reset(self, *args):
        """Nuke the complete configuration."""
        self.config = self.DEFAULT_ROUTES_CONFIG
        self.save_config()
        return 'Done. All configuration has been expunged.'

    def routes_defaults(self, message, args):
        """Get or set what events are relayed by default for new routes."""
        if args:
            events = []
            for event in args:
                if event in self.AVAILABLE_EVENTS:
                    events.append(event)
                else:
                    yield self.EVENT_UNKNOWN.format(event)
            self.set_defaults(events)
            yield md_escape(
                'Done. Newly created routes will default to '
                'receiving: {0}.'.format(' '.join(events)))
        else:
            yield md_escape('Events routed by default: {0}.'.format(
                ' '.join(self.get_defaults())))

    def routes_add_route(self, message, args):
        """Map a project to a chatroom, essentially creating a route.

        This takes two or three arguments: author/project, a chatroom and
        optionally a list of events.

        If you do not specify a list of events the route will default to
        receiving the events configured as 'default_events'.
        """
        if len(args) >= 2:
            project = args[0]
            room = args[1]
            # Slicing on an index that, potentially, doesn't exist returns
            # an empty list instead of raising an IndexError
            events = args[2:]

            if not self.has_route(project, room):
                self.set_route(project, room)

            if events:
                for event in events[:]:
                    if event not in self.ATLASSIAN_EVENTS:
                        events.remove(event)
                        yield self.EVENT_UNKNOWN.format(event)
            else:
                events = self.get_defaults()
            self.set_events(project, room, events)
            yield ('Done. Relaying messages from {0} to {1} for '
                   'events: {2}'.format(project, room, ' '.join(events)))
        else:
            yield self.HELP_MSG

    def routes_list_routes(self, message, args):
        """Displays the routes for one, multiple or all projects."""
        if args:
            for project in args:
                if self.has_project(project):
                    yield self.show_project_config(project)
                else:
                    yield self.PROJECT_UNKNOWN.format(project)
        else:
            projects = self.get_projects()
            if projects:
                yield ("You asked for it, here are all the projects, the "
                       "rooms and associated events that are relayed:")
                for project in projects:
                    yield self.show_project_config(project)
            else:
                yield 'No projects configured, nothing to show.'

    def routes_remove(self, message, args):
        """Remove a route or a project.

        If only one argument is passed all configuration for that project
        is removed.

        When two arguments are passed that specific route is removed. If this
        was the last route any remaining configuration for the project is
        removed too. With only one route remaining this essentially achieves
        the same result as calling this with only the project as argument.
        """
        if len(args) == 1:
            project = args[0]
            self.clear_project(project)
            yield 'Removed all configuration for {0}.'.format(project)
        elif len(args) == 2:
            project = args[0]
            room = args[1]
            self.clear_route(project, room)
            yield 'Removed route for {0} to {1}.'.format(project, room)
            if not self.get_routes(project):
                self.clear_project(project)
                yield ('No more routes for {0}, removing remaining '
                       'configuration.'.format(project))
        else:
            yield self.HELP_MSG

    def routes_global(self, message, args):
        """Set a global route"""
        if len(args) == 1:
            self['global_route'] = None
            yield 'Removed global route.'
        elif len(args) == 2:
            room = args[1]
            self['global_route'] = room
            yield 'Set global route to {}.'.format(room)
        else:
            yield self.HELP_MSG

    def validate_incoming(self):
        return True  # override to add special validation

    def routes_receive(self, request):
        self.log.info(request.json)
        if not self.validate_incoming(request):
            abort(400)

        body = request.json
        event_type = body['webhookEvent']
        project = body['issue']['fields']['project']['key'] if 'issue' in body else None

        global_event = self.is_global_event(event_type, project, body)

        if self.get_project(project) is None and not global_event:
            # Not a project we know so accept the payload, return 200 but
            # discard the message
            self.log.info('Message received for {0} but no such project '
                          'is configured'.format(project))
            response.status = 204
            return None

        message = self.get_message(body, project, event_type)

        # - if we have a message and is it not empty or None
        # - get all rooms for the project we received the event for
        # - check if we should deliver this event
        # - join the room (this won't do anything if we're already joined)
        # - send the message
        if message and message is not None:
            for room_name in self.get_routes(project):
                events = self.get_events(project, room_name)
                if event_type in events or '*' in events:
                    self.join_and_send(room_name, message)
            if global_event and self.get('global_route'):
                self.join_and_send(self['global_route'], message)
        response.status = 204
        return None

    def get_message(self, body, project, event_type, generic_fn=None):
        """
        Dispatch the message. Check explicitly with hasattr first. When
        using a try/catch with AttributeError errors in the
        message_function which result in an AttributeError would cause
        us to call msg_generic, which is not what we want.
        """
        if generic_fn is None:
            generic_fn = self.msg_generic

        message_function = 'msg_{0}'.format(event_type.replace(':', '_'))
        if hasattr(self, message_function):
            message = getattr(self, message_function)(body, project)
        else:
            message = generic_fn(body, project, event_type)
        return message

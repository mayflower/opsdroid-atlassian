##########
err-tlassian
##########

err-atlassian is a webhook endpoint for Err_ as well as a set of commands to
configure the routing of messages to chatrooms.

This plugin does not depend on anything but Err_ itself and the Python
standard library.

The supported Python versions are:

* Python 2.7+
* Python 3.3+


Webhooks
--------

Webhooks are a way for websites, or really any service, to notify another
service that something happened. JIRA and Confluence provide webhooks that based on
an event send a payload over HTTP to another service which can then react
accordingly.

They enable near real-time notifications of actions, so if changes happen in JIRA/Confluence,
it will send a HTTP payload with some information about that event.

This mechanism can be used to receive almost instantaneous notifications of
activity that happens in JIRA/Confluence. It's a great way to hook up
your project to Err_.

Installation
------------

To be able to use webhooks with Err_ you'll need to configure its
built-in webserver first using the ``!webserver`` command once you've loaded
the webserver plugin.

We **strongly** advise you to not expose the webserver plugin directly to
the internet but instead put it behind a proxying nginx or Apache HTTPD
and let those handle terminating SSL traffic for you and passing the
request on to Err_'s webserver.

The webhook on JIRA/Confluence needs to be configured to send a payload to
https://your-endoint.tld/atlassian

Configuration
-------------

Most Err_ plugins can be configured using the ``!config PluginName`` action.
However, since this plugin has to handle fairly complex configuration
separate commands were created for you to set everything up and interact
with this plugin's settings.

To view the full configuration of the plugin you can issue the following:

.. code-block:: text

   !atlassian config

There is no way to manipulate the configuration through this command, only
view it.

Usage
-----

route
^^^^^

The ``route`` command is the first to be executed when adding a new project
for which events will be forwarded. It takes as arguments the project key
and the channel you want messages routed to:

.. code-block:: text

   !atlassian route KEY example@example.com

routes
^^^^^^

In order to list all the routes for a project:

.. code-block:: text

   !atlassian routes KEY

You can pass multiple projects to ``!atlassian routes`` by separating them
with a space. In return you'll get the route configuration for every of those
projects.

.. code-block:: text

   !atlassian routes KEY TEST

If you want to list all routes simply call the command with no arguments:

.. code-block:: text

   !atlassian routes

default events
^^^^^^^^^^^^^^

The default events to subscribe on can be altered:

.. code-block:: text

   !atlassian defaults jira:issue_created user_deleted

Changing the default will only affect new routes, existing ones will have
to be updated manually using the ``route`` command.

Issuing that same command without any events will list the currently active
defaults:

.. code-block:: text

   !atlassian defaults

remove
^^^^^^

In order to remove a route issue the following:

.. code-block:: text

   !atlassian remove KEY example@example.com

If this is the last route we know about for that project any further
configuration entries for that project will be removed too, like the
token.

Should you wish to remove all routes, essentially removing the project:

.. code-block:: text

   !atlassian remove KEY

This will also cause the bot to remove any further configuration entries it
has stored for this project, such as the token.

Commands
--------

A complete overview of the commands.

+----------+---------------------------------+----------------------------------------------------------------------+
| Command  | Arugment(s)                     | Result                                                               |
+==========+=================================+======================================================================+
| help     |                                 | show usage information                                               |
+----------+---------------------------------+----------------------------------------------------------------------+
| route    | <project> <channel>             | relay messages for <project> to <channel>                            |
+----------+---------------------------------+----------------------------------------------------------------------+
| route    | <project> <channel> <events>    | relay messages triggered by <events> from <project> to <channel>     |
+----------+---------------------------------+----------------------------------------------------------------------+
| routes   |                                 | show all repositories and routes                                     |
+----------+---------------------------------+----------------------------------------------------------------------+
| routes   | <project>                       | show all routes for <project>                                        |
+----------+---------------------------------+----------------------------------------------------------------------+
| routes   | <project> <project>             | show all routes for multiple <project>'s                             |
+----------+---------------------------------+----------------------------------------------------------------------+
| defaults |                                 | show all current defaults                                            |
+----------+---------------------------------+----------------------------------------------------------------------+
| defaults | <events>                        | what events should be relayed by default                             |
+----------+---------------------------------+----------------------------------------------------------------------+


Contributing
------------

This plugin is in its early stages but should be usable. However, since
there's a lot of different event types with different actions it might not be
able to gracefully deal with them all just yet and bugs may arise.

Right now we support:

...

Feel free to submit pull requests for new features and fixes or issues if you
encounter problems using this plugin.

License
-------

This code is quasi-forked from https://github.com/daenney/err-githubhook, thanks to @daenney for his work there.
This code is licensed under the GPLv3, see the LICENSE file.

.. _Err: http://errbot.net

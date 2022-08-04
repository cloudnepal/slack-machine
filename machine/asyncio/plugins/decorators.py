from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Union, cast
from pyee.asyncio import AsyncIOEventEmitter

from typing_extensions import ParamSpec
from typing_extensions import Protocol

ee = AsyncIOEventEmitter()


@dataclass
class PluginActions:
    process: list[str] = field(default_factory=list)
    listen_to: list[re.Pattern[str]] = field(default_factory=list)
    respond_to: list[re.Pattern[str]] = field(default_factory=list)


@dataclass
class Metadata:
    plugin_actions: PluginActions = field(default_factory=PluginActions)
    required_settings: list[str] = field(default_factory=list)


P = ParamSpec("P")


class DecoratedPluginFunc(Protocol[P]):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        ...

    metadata: Metadata


def process(slack_event_type: str) -> Callable[[Callable[P, None]], DecoratedPluginFunc[P, None]]:
    """Process Slack events of a specific type

    This decorator will enable a Plugin method to process `Slack events`_ of a specific type. The
    Plugin method will be called for each event of the specified type that the bot receives.
    The received event will be passed to the method when called.

    .. _Slack events: https://api.slack.com/events

    :param slack_event_type: type of event the method needs to process. Can be any event supported
        by the RTM API
    :return: wrapped method
    """

    def process_decorator(f: Callable[P, None]) -> DecoratedPluginFunc[P, None]:
        f = cast(DecoratedPluginFunc, f)
        f.metadata = getattr(f, "metadata", Metadata())
        f.metadata.plugin_actions.process.append(slack_event_type)
        return f

    return process_decorator


def listen_to(
    regex: str, flags: re.RegexFlag | int = re.IGNORECASE
) -> Callable[[Callable[P, None]], DecoratedPluginFunc[P, None]]:
    """Listen to messages matching a regex pattern

    This decorator will enable a Plugin method to listen to messages that match a regex pattern.
    The Plugin method will be called for each message that matches the specified regex pattern.
    The received :py:class:`~machine.plugins.base.Message` will be passed to the method when called.
    Named groups can be used in the regex pattern, to catch specific parts of the message. These
    groups will be passed to the method as keyword arguments when called.

    :param regex: regex pattern to listen for
    :param flags: regex flags to apply when matching
    :return: wrapped method
    """

    def listen_to_decorator(f: Callable[P, None]) -> DecoratedPluginFunc[P, None]:
        f = cast(DecoratedPluginFunc, f)
        f.metadata = getattr(f, "metadata", Metadata())
        f.metadata.plugin_actions.listen_to.append(re.compile(regex, flags))
        return f

    return listen_to_decorator


def respond_to(
    regex: str, flags: re.RegexFlag | int = re.IGNORECASE
) -> Callable[[Callable[P, None]], DecoratedPluginFunc[P, None]]:
    """Listen to messages mentioning the bot and matching a regex pattern

    This decorator will enable a Plugin method to listen to messages that are directed to the bot
    (ie. message starts by mentioning the bot) and match a regex pattern.
    The Plugin method will be called for each message that mentions the bot and matches the
    specified regex pattern. The received :py:class:`~machine.plugins.base.Message` will be passed
    to the method when called. Named groups can be used in the regex pattern, to catch specific
    parts of the message. These groups will be passed to the method as keyword arguments when
    called.

    :param regex: regex pattern to listen for
    :param flags: regex flags to apply when matching
    :return: wrapped method
    """

    def respond_to_decorator(f: Callable[P, None]) -> DecoratedPluginFunc[P, None]:
        f = cast(DecoratedPluginFunc, f)
        f.metadata = getattr(f, "metadata", Metadata())
        f.metadata.plugin_actions.respond_to.append(re.compile(regex, flags))
        return f

    return respond_to_decorator


def on(event: str) -> Callable[[Callable[P, None]], Callable[P, None]]:
    """Listen for an event

    The decorated function will be called whenever a plugin (or Slack Machine itself) emits an
    event with the given name.

    :param event: name of the event to listen for. Event names are global
    """

    def on_decorator(f: Callable[P, None]) -> Callable[P, None]:
        ee.add_listener(event, f)
        return f

    return on_decorator


def required_settings(settings: Union[list[str], str]) -> Callable[[Callable[P, None]], DecoratedPluginFunc[P, None]]:
    """Specify a required setting for a plugin or plugin method

    The settings specified with this decorator will be added to the required settings for the
    plugin. If one or more settings have not been defined by the user, the plugin will not be
    loaded and a warning will be written to the console upon startup.

    :param settings: settings that are required (can be list of strings, or single string)
    """

    def required_settings_decorator(f_or_cls: Callable[P, None]) -> DecoratedPluginFunc[P, None]:
        f_or_cls = cast(DecoratedPluginFunc, f_or_cls)
        f_or_cls.metadata = getattr(f_or_cls, "metadata", Metadata())
        if isinstance(settings, list):
            f_or_cls.metadata.required_settings.extend(settings)
        elif isinstance(settings, str):
            f_or_cls.metadata.required_settings.append(settings)
        return f_or_cls

    return required_settings_decorator
from enum import Enum


class StatusEnums(Enum):
    """
    Represents an enumeration of statuses for a process.

    This class defines a set of status values that can be used to represent
    the state of a process. It includes predefined statuses and provides
    a method to retrieve these statuses as a list of choices.
    """

    NOT_STARTED = "Not Started"
    IN_PROGRESS = "In Progress"
    DEMONSTRATED = "Demonstrated"
    FAILED = "Failed"

    @classmethod
    def choices(cls):
        return [(key.name, key.value) for key in cls]


class MessageRolesEnum(Enum):
    """
    Enumeration class for defining roles in a messaging system.

    This class provides an enumerated set of roles that are commonly used in
    messaging systems such as system-level roles, user roles, and assistant
    roles. It also includes a helper method to extract choices in a structured
    format for further use.
    """

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

    @classmethod
    def choices(cls):
        return [(key.name, key.value) for key in cls]

from typing import List, Union
from chainless.messages import UserMessage, AssistantMessage

class Memory:
    """
    Memory class for storing conversational messages in a lightweight,
    sliding-window fashion. Designed to be simple, safe, and professional
    for developers to integrate with Chainless agents.

    Features:
    - Sliding window: only stores the last `max_messages` messages.
    - Separate methods for user and assistant messages.
    - Error handling and type checking to prevent misuse.
    - Minimalist API: add messages and retrieve the current memory.

    Parameters:
    -----------
    max_messages : int
        Maximum number of messages to keep in memory.
        Older messages are automatically discarded when this limit is exceeded.

    Example:
    --------
    >>> memory = Memory(max_messages=10)
    >>> memory.add_user("Hello!")
    >>> memory.add_assistant("Hi there!")
    >>> agent.run(message_history=memory.get())
    """

    def __init__(self, max_messages: int = 50):
        if not isinstance(max_messages, int) or max_messages <= 0:
            raise ValueError("max_messages must be a positive integer")
        self.max_messages = max_messages
        self._messages: List[Union[UserMessage, AssistantMessage]] = []

    def add_user(self, content: str):
        """
        Add a user message to memory.

        Parameters:
        -----------
        content : str
            The text content of the user's message.

        Raises:
        -------
        TypeError: If content is not a string.
        """
        if not isinstance(content, str):
            raise TypeError("User message content must be a string")
        self._add(UserMessage(content=content))

    def add_assistant(self, content: str):
        """
        Add an assistant message to memory.

        Parameters:
        -----------
        content : str
            The text content of the assistant's message.

        Raises:
        -------
        TypeError: If content is not a string.
        """
        if not isinstance(content, str):
            raise TypeError("Assistant message content must be a string")
        self._add(AssistantMessage(content=content))

    def _add(self, message: Union[UserMessage, AssistantMessage]):
        """Internal method to append a message and enforce max_messages."""
        self._messages.append(message)
        if len(self._messages) > self.max_messages:
            # Keep only the most recent messages
            self._messages = self._messages[-self.max_messages :]

    def get(self) -> List[Union[UserMessage, AssistantMessage]]:
        """
        Retrieve the current memory as a list of messages.

        Returns:
        --------
        List[Union[UserMessage, AssistantMessage]] : The list of stored messages,
        ordered from oldest to newest.
        """
        return self._messages.copy()

    def clear(self):
        """
        Clear all messages from memory.
        """
        self._messages.clear()

from abc import ABC, abstractmethod


class Notifier(ABC):
    ''' Sends notifications based on user-defined rules.
    '''

    @abstractmethod
    def post(self, **kwargs):
        """ Send a single notifiaction.

        The notification is sent asynchronously.
        """
        raise NotImplementedError



class Notifier(object):
    ''' Sends notifications based on user-defined rules.
    '''

    def post(self, **kwargs):
        """ Send a single notifiaction.

        The notification is sent asynchronously.
        """
        raise NotImplementedError

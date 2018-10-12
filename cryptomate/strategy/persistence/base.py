from abc import ABC, abstractmethod


class Persister(ABC):
    ''' Persists strategy state so it can be recovered.
    '''

    @abstractmethod
    def __iter__(self):
        ''' Return an iterator of all persisted state keys. '''
        raise NotImplementedError

    @abstractmethod
    def __getitem__(self, key):
        ''' Retrieve state for given key

        :param int key: State identifier.
        :rtype: bytes
        '''
        raise NotImplementedError

    @abstractmethod
    def __setitem__(self, key, state):
        ''' Save state as given key

        :param int key: State identifier.
        :param bytes state: State data to save. Must be convertible to a bytes object.
        '''
        raise NotImplementedError

    @abstractmethod
    def __delitem__(self, key):
        ''' Return saved state for given key

        :param int key: State identifier.
        '''
        raise NotImplementedError

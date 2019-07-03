"""Async connection class."""
import json
import logging
import os

from aiohttp.client import _RequestContextManager

from O365.aio.connection_base import ConnectionBase
from O365.aio.oauth2_session import OAuth2Session as aio_OAuth2Session

_LOGGER = logging.getLogger(__name__)


class aio_Connection(ConnectionBase):  # pylint: disable=invalid-name
    """Async version."""

    async def request_token(
            self, *, authorization_url, store_token=True, token_path=None):
        """ Authenticates for the specified url and gets the token, save the
        token for future based if requested

        :param str authorization_url: url given by the authorization flow
        :param bool store_token: whether or not to store the token in file
         system, so u don't have to keep opening the auth link and
         authenticating every time
        :param Path token_path: full path to where the token should be saved to
        :return: Success/Failure
        :rtype: bool
        """
        assert not store_token, "Store token not implemented yet"

        if self.session is None:
            raise RuntimeError("Fist call 'get_authorization_url' to "
                               "generate a valid oauth object")

        client_id, client_secret = self.auth

        # Allow token scope to not match requested scope.
        # (Other auth libraries allow this, but Requests-OAuthlib
        # raises exception on scope mismatch by default.)
        os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
        os.environ['OAUTHLIB_IGNORE_SCOPE_CHANGE'] = '1'

        try:
            self.token = await self.session.fetch_token(
                token_url=self._oauth2_token_url,
                authorization_response=authorization_url,
                client_id=client_id,
                client_secret=client_secret)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Unable to fetch auth token. Error: %s", err)
            return False

        if token_path:
            self.token_path = token_path
        self.store_token = store_token

        return True

    def _session_init(self, *args, **kwargs):
        """Init session specific per transport provider request/aiohttp"""
        self.session = aio_OAuth2Session(*args, trust_env=True, **kwargs)

    async def request(self, method, url, custom_session=None, **kwargs):
        """ Makes a request to url using an oauth session

        :param str url: url to send request to
        :param str method: type of request (get/put/post/patch/delete)
        :param custom_session: a requests session if not default session.
        :param kwargs: extra params to send to the request api
        :return: Response of the request
        :rtype: requests.Response
        """
        session = custom_session or self.session or self.get_session()

        assert method in self._allowed_methods, \
            'Method must be one of the allowed ones'

        if method == 'GET':
            kwargs.setdefault('allow_redirects', True)
        elif method in ['post', 'put', 'patch']:
            kwargs.setdefault('headers', {})
            kwargs['headers'].setdefault('Content-type', 'application/json')
            if 'data' in kwargs and \
                    kwargs['headers']['Content-type'] == 'application/json':
                kwargs['data'] = json.dumps(
                    kwargs['data'])  # auto convert to json

        response = await session.request(method, url, **kwargs)

        return response

    def get(self, url, **kwargs):
        """get."""
        return _RequestContextManager(self.request('get', url, **kwargs))

    def post(self, url, **kwargs):
        """post."""
        return _RequestContextManager(self.request('post', url, **kwargs))

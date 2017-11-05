from flask_session.sessions import ServerSideSession, SessionInterface
from .domain import Domain
import dateutil.parser
from datetime import datetime
from itsdangerous import Signer, BadSignature, want_bytes


import simplejson

class SDBSession(ServerSideSession):
    pass


class SDBSessionInterface(SessionInterface):
    """A Session interface that uses AWS SDB as backend.
    :param client: A boto3 SDB client instance.
    :param domain: The domain you want to use.
    :param collection: The collection you want to use.
    :param key_prefix: A prefix that is added to all MongoDB store keys.
    :param use_signer: Whether to sign the session id cookie or not.
    :param permanent: Whether to use permanent session or not.
    """

    serializer = simplejson
    session_class = SDBSession

    def __init__(self, client, domain, key_prefix, use_signer=False,
                 permanent=True):
        self.client = client
        self.domain = Domain(client, domain)
        self.key_prefix = key_prefix
        self.use_signer = use_signer
        self.permanent = permanent

    def open_session(self, app, request):
        sid = request.cookies.get(app.session_cookie_name)
        if not sid:
            sid = self._generate_sid()
            return self.session_class(sid=sid, permanent=self.permanent)
        if self.use_signer:
            signer = self._get_signer(app)
            if signer is None:
                return None
            try:
                sid_as_bytes = signer.unsign(sid)
                sid = sid_as_bytes.decode()
            except BadSignature:
                sid = self._generate_sid()
                return self.session_class(sid=sid, permanent=self.permanent)

        store_id = self.key_prefix + sid
        document = self.domain.get_consistent(store_id)

        expiration = None
        if document and len(document.get('expiration', '')) > 0:
            expiration = document['expiration']

        if document and expiration and dateutil.parser.parse(expiration) <= datetime.utcnow():
            # Delete expired session
            self.domain.remove(store_id)
            document = None

        if document is not None:
            try:
                val = document['val']
                data = self.serializer.loads(want_bytes(val))
                return self.session_class(data, sid=sid)
            except Exception as e:
                return self.session_class(sid=sid, permanent=self.permanent)
        return self.session_class(sid=sid, permanent=self.permanent)

    def save_session(self, app, session, response):
        domain = self.get_cookie_domain(app)
        path = self.get_cookie_path(app)
        store_id = self.key_prefix + session.sid
        if not session:
            if session.modified:
                self.domain.remove(store_id)
                response.delete_cookie(app.session_cookie_name,
                                       domain=domain, path=path)
            return

        httponly = self.get_cookie_httponly(app)
        secure = self.get_cookie_secure(app)
        expires = self.get_expiration_time(app, session)
        val = self.serializer.dumps(dict(session))
        expiration = ''
        if expires:
            expiration = expires.isoformat()

        data = {
            'id': store_id,
            'val': val,
            'expiration': expiration,
            'modified': datetime.now().isoformat()
        }

        self.domain.update(store_id, data)

        if self.use_signer:
            session_id = self._get_signer(app).sign(want_bytes(session.sid))
        else:
            session_id = session.sid
        response.set_cookie(app.session_cookie_name, session_id,
                            expires=expires, httponly=httponly,
                            domain=domain, path=path, secure=secure)

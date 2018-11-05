import contextlib
import pytest


class TemporaryCertificate:
    ''' Certificate representation used by :func:`ssl_certificate` fixture '''
    def __init__(self, cert_file, key_file):
        self._cert_file = cert_file
        self._key_file = key_file

    def load_into(self, context):
        ''' Load the certificate with its private key for authentication purposes.

        :param context: a SSL context that will be associated with the server.
        :type context: ssl.SSLContext
        '''
        context.load_cert_chain(self._cert_file.name, keyfile=self._key_file.name)

    def allow_verify(self, context):
        ''' Load the certificate for verification purposes.

        :param context: a SSL context that will be associated with the server.
        :type context: ssl.SSLContext
        '''
        context.load_verify_locations(cafile=self._cert_file.name)


@pytest.fixture(scope='session')
def ssl_certificate():
    ''' Self-signed certificate fixture, used for local server tests.

    :rtype: TemporaryCertificate
    '''

    import datetime
    import tempfile
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    subject = issuer = x509.Name([x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, 'localhost')])

    with contextlib.ExitStack() as stack:
        key = rsa.generate_private_key(
            public_exponent=65537, key_size=1024,
            backend=default_backend()
        )

        key_file = stack.enter_context(tempfile.NamedTemporaryFile())
        key_file.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
        key_file.flush()


        cert = (x509.CertificateBuilder().subject_name(subject)
                                         .issuer_name(issuer)
                                         .public_key(key.public_key())
                                         .serial_number(x509.random_serial_number())
                                         .not_valid_before(datetime.datetime.utcnow())
                                         .not_valid_after(datetime.datetime.utcnow() +
                                                          datetime.timedelta(days=1))
                                         .add_extension(
                                             x509.SubjectAlternativeName([
                                                 x509.DNSName('localhost'),
                                                 x509.DNSName('127.0.0.1'),
                                             ]),
                                             critical=False,
                                         )
                                         .sign(key, hashes.SHA256(), default_backend()))

        cert_file = stack.enter_context(tempfile.NamedTemporaryFile())
        cert_file.write(cert.public_bytes(serialization.Encoding.PEM))
        cert_file.flush()

        yield TemporaryCertificate(cert_file, key_file)

from cryptography import x509
import inventory
import target
import date.date

    # Table Definition:

    # SQL> desc dbc_team.cert_info
    #  Name                                      Null?    Type
    #  ----------------------------------------- -------- ----------------------------
    #  CERT_ID                                   NOT NULL NUMBER(5)
    #  HOST_INVENTORY_ID                              NOT NULL NUMBER(5)
    #  CSR                                                VARCHAR2(2048)
    #  CERTIFICATE_BODY                                   VARCHAR2(4000)
    #  BEGIN_DATE                                         VARCHAR2(50)
    #  END_DATE                                           DATE
    #  CERT_TYPE                                          VARCHAR2(25)
    #  PASSWORD                                           VARCHAR2(2048)
    #  PORT                                               NUMBER(5)
    #  CIPHERS                                            VARCHAR2(255)
    #  SSL_VERSION                                        NUMBER(1,2)
    #  DN                                                 VARCHAR2(255)
    #  ISSUER                                             VARCHAR2(100)
    #  ROOT                                               VARCHAR2(50)
    #  INTERMEDIATE                                       VARCHAR2(50)
    #  NOTES                                              VARCHAR2(255)
    #  COMMON_NAME                                        VARCHAR2(60)
    #  OWNER                                              VARCHAR2(60)
    #  WALLET_DIR                                         VARCHAR2(60)


class certificate:

    def __init__(self, cert_id, subject, issuer, serial_number, not_valid_before,
                 not_valid_after, key_algorithm, sig_algorithm):
        self.cert_id = cert_id
        self.subject = subject
        self.issuer = issuer
        self.serial_number = serial_number
        self.not_valid_before = not_valid_before
        self.not_valid_after = not_valid_after
        self.key_algorithm = key_algorithm
        self.sig_algorithm = sig_algorithm


    def __str__(self):
        target_dict = {
            'cert_id': self.cert_id,
            'subject': self.subject,
            'issuer': self.issuer,
            'serial_number': self.serial_number,
            'not_valid_before': self.not_valid_before,
            'not_valid_after': self.not_valid_after,
            'key_algorithm': self.key_algorithm,
            'sig_algorithmself': self.sig_algorithm 
        }



    def get_csr(hostname, wallet_type, location):
        """ Return the CSR text for this host from a) apex if we have it, else b) the server"""
        csr=''
        return csr 

    def save_csr(CSR):
        # Parse the CSR and then Insert / update the CSR text in APEX 
        rc=1
        return rc

    def get_cert(hostname, wallet_type, location):
        """Return the most recent signed certificate text from a) APEX if we have it, else b) the server if we can find it.
           Note: When renewing, we might have 2 active for a short period"""
        cert=certificate()
        return cert

    def save_cert(certificate):
        """Parse the supplied certificate and then Insert / update the Cert text in APEX 
        hostname, path, os_owner, app_owner, type, algorithm, password,  key_text, begin_dt, end_dt, notes)"""

    def cert_info(PEM):
        # Parse a certificate PEM and return a certificate object.
        cert=certificate()


    def parse_pem_certificate(pem_cert):
        """ Parses a PEM-encoded certificate and displays its information.

        Args:
        pem_cert: A string containing the PEM-encoded certificate.
        """

        # Load the PEM-encoded certificate.
        certificate = x509.load_pem_x509_certificate(pem_cert.encode('ascii'))

        return certificate
                                            
    def days_left(certificate):
        # Parse the certificate and return the difference between the certificate's end date 
        # and the current date in days.
        days_left = certificate.not_valid_after - date.today()
        return days_left


    def replace_cert(certificate):
        # Put the new certificate (supplied) into the server
        return 0


    def validate_Cert(Certificate, csr):
        # Get the hostname and checksum of the supplied certificate and then 
        # get the CSR and it's cshksum and see if they match
        return True


    def same_issuer_chain(certificate, location):
        # Compare the issuers of the new certificate with the wallet location 
        # and return TRUE if they are the same.
        return True


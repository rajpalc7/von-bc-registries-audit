import logging
import os
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
from smtplib import SMTP, SMTPException

LOGGER = logging.getLogger(__name__)


def email_support(payload):
    server_addr = os.getenv("SMTP_SERVER_ADDRESS")
    recip_email = os.getenv("FEEDBACK_TARGET_EMAIL")
    if recip_email:
        recip_email = recip_email.split(",")

    from_name = "BC Registries Audit"
    from_email = "no-reply@bcregaudit.gov.bc.ca"

    subject = "BC Reg Audit: {}".format(payload["friendlyProjectName"])

    if server_addr and recip_email:
        body = "Nightly audit report for {}\n".format(payload["friendlyProjectName"])
        body = "{}Status Code: {}\n\n".format(body, payload["statusCode"])
        body = "{}{}".format(body, payload["message"])
        msg = MIMEText(body, "plain")
        recipients = ",".join(recip_email)
        from_line = formataddr((str(Header(from_name, "utf-8")), from_email))
        msg["Subject"] = subject
        msg["From"] = from_line
        msg["To"] = recipients

        print(">>> connecting to smtp:", server_addr)
        with SMTP(server_addr) as smtp:
            print(">>> sending email ...")
            smtp.sendmail(from_line, recip_email, msg.as_string())
            print("    ... sent!!!")

        return True

    return False

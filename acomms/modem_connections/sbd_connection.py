__author__ = 'andrew'

#from acomms.modem_connections import
from threading import Thread
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import email, os
from time import sleep
import imaplib
import datetime

class SBDConnection(object):
    def __init__(self, modem, IMEI,
                 email_account='acomms-support@whoi.edu',
                 username = None,pw = None,
                 check_rate = 30,
                 imap_srv = "imap.whoi.edu", imap_port = 143,
                 smtp_svr = "outbox.whoi.edu", smtp_port = 25):
        self.modem = modem
        self.SUBJECT = IMEI
        self.FROM = email_account
        self.email_username = username
        self.email_userpw = pw
        self.IMEI = IMEI
        self.email_check_rate = check_rate
        self.email_incoming_svr = imap_srv
        self.email_outgoing_svr = smtp_svr
        self.email_outgoing_port = smtp_port
        self.email_incoming_port = imap_port
        self.last_read = datetime.date.now()
        self._thread = Thread(target=self._listen)
        self._thread.setDaemon(True)
        self._thread.start()


    @property
    def is_connected(self):
        return True

    @property
    def can_change_baudrate(self):
        return False

    def change_baudrate(self,baudrate):
        return 9600

    def _listen(self):
        while True:
            date = (datetime.date.now() - datetime.timedelta(1)).strftime("%d-%b-%Y")
            M = imaplib.IMAP4(self.email_incoming_svr, self.email_incoming_port)
            if self.email_username is not None:
                response, details = M.login(self.email_userpw, self.email_userpw)
            M.select('INBOX')
            #Limit our search to Unseen Messages for our IMEI in the Past 24 Hours
            response, items = M.search(None,
                                       '(UNSEEN SENTSINCE {date} HEADER Subject "SBD Msg From Unit: {IMEI}" FROM "sbdservice@sbd.iridium.com")'.format(
                                           date=date,
                                           IMEI=300125010116840))
            for emailid in items[0].split():
                response, data = M.fetch(emailid, '(RFC822)')
                mail = email.message_from_string(data[0][1])

                if not mail.is_multipart():
                    continue
                for part in mail.walk():
                    if part.is_multipart():
                        continue
                    if part.get('Content-Disposition') is None:
                        continue
                    file_nm = part.get_filename()
                    if file_nm is None:
                        continue
                    filename, fileext = os.path.splitext(file_nm)
                    if fileext != '.sbd':
                        continue
                    msg = part.get_payload(decode=True)
                    for line in msg.splitlines(True):
                        self.modem._process_incoming_nmea(line)
                    temp = M.store(emailid,'+FLAGS', '\\Seen')

            M.close()
            M.logout()
            self.modem._process_outgoing_nmea()
            sleep(self.email_check_rate * 60) # Wait a minute and try again.

    def write(self,msg):
        email_msg = MIMEMultipart()
        email_msg['Subject'] = "{0}".format(self.IMEI)
        email_msg['To'] = 'data@sbd.iridium.com'
        email_msg['From'] = "{0}".format(self.FROM)

        part = MIMEText(msg)
        email_msg.attach(part)

        attachment = MIMEApplication(msg)

        attachment.add_header('Content-Disposition', 'attachment',
                                filename="{0}.sbd".format((datetime.datetime.utcnow()).strftime("%d%b%YT%H%M%S%z")))
        email_msg.attach(attachment)

        smtp = smtplib.SMTP()
        smtp.connect(self.email_outgoing_svr,  self.email_outgoing_port)
        smtp.sendmail(self.FROM,['data@sbd.iridium.com', self.FROM], email_msg.as_string())
        smtp.quit()
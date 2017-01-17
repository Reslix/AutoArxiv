"""
This is the file where all the outside communication functions happen. 

Emails are sent and received here, and the commands relayed are
handled here. 

For each article in the current table, a list of users and ratings
are generated. Ratings higher than a certain threshold, which may 
be customized later on, 
"""

import smtplib
import imaplib
import email
import maintain as m
import re

class Emailer():
    """
    A poorly constructed email send/recieve class that will probably never get better. 
    """
    def __init__(self, identity='listbot', email, passwd):
        """
        Just some initliazations.
        """
        self.email = email
        self.passwd = passwd
        self.identity = identity

    def send_listing(self,email,listing):
        """
        Formats the sorted listing into some readable plaintext form. Hasn't been tested, so this will prove to be interesting.
        """
        try:  
            self.server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            self.limit = 500 #Gmail limits me to this many free sent messages, probably to prevent spam. 
            self.server.ehlo()
            self.server.login(self.email, self.passwd)

        except:  
            print('Unable to connect to smtp')

        if len(listing) == 0:
            message = "No new articles"
        else:
            message = ""
            for i,msg in enumerate(listing):
                message = message + str(i) + '. ' + str(msg[0]) + ', ' + str(msg[2]) + ', ' + str(msg[3]) + ', ' + str(msg[1]) + '|| \n'
        message = message + """To update your ratings for an article, send a new email to the server with the
                                listing formatted as seen above, with new ratings replacing the old ones. Enclose
                                text body in double paretheses (()) to assist with email parsing."""
        self.server.sendmail(self.email,email, str(len(listing)) + " New listings, ordered by relevance", message)
        print("Sent listing to " + email)
        self.server.quit()

    def receive_emails(self):
        """
        I am honestly not sure if this will work, but the intension is to read all new
        emails from the server and run commands sent by users. For the time being, 
        all this supposedly does is update ratings in the preferences table for any 
        article id that exists. 
        """
        try:  
            self.mail = imaplib.IMAP4_SSL('imap.gmail.com')
            self.mail.login(self.email, self.passwd)
        except:  
            print('Unable to connect to imap')
        self.mail.select('inbox')
        self.rawmessage = []
        retcode, data = self.mail.search(None, '(UNSEEN)')
        for num in data[0].split():
            typ, data = self.mail.fetch(num,'(RFC822)')
            msg = email.message_from_string(str(data[0][1]))
            typ, data = self.mail.store(num,'+FLAGS','\\Seen')
            self.rawmessage.append(msg)

        for message in self.rawmessage:
            sender = re.search('<.*>',re.search('From: .+ <.+@.+>.*To',message.as_string()).group()).group()
            print(sender)
            sender = sender[1:-1]
            commands = re.search('((.*))',message.as_string())
            if commands != None:
                commands = commands.group()[2:-2].split('||')
                for i in range(len(commands)):
                    print(commands[i])
                    commands[i] = commands[i].strip()
                    command = commands[i].split(', ')
                    m.set_user_rating(command[0],sender,command[1])

        self.mail.close()
import re
import email
import imaplib
from django.core.mail import send_mail

from autoarxiv import settings
from warden.models import Author, AuthorRating, Article, ArticleRating, Member


def send_listing(e_mail, listing):
    """
    Formats the sorted listing into some readable plaintext form. Hasn't been tested, so this will prove to be interesting.
    """

    if len(listing) == 0:
        message = "No new articles"
    else:
        message = "\n"
        for i, msg in enumerate(listing):
            message = message + msg + '\n\n'

    message = message + """\n\nTo update ratings for an article or author, send an email (not a reply!) to this sender address with
                                ARTICLE or AUTHOR in the subject line. 
                                
                                For articles, list line-by-line the article Arxiv ID as it came in the listing and an
                                integer rating between 1 and 5, separated by a comma.
                                
                                For authors, do the same with the author's name or email address and have the rating added
                                in the same way."""

    send_mail(str(len(listing)) + ' New listings, ordered by relevance',
              message,
              settings.EMAIL_HOST_USER,
              [e_mail])

    print("Sent listing to " + e_mail)


def receive_emails():
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    except:
        print('Unable to connect to imap')
    mail.select('inbox')
    rawmessage = []
    retcode, data = mail.search(None, '(UNSEEN)')
    for num in data[0].split():
        typ, data = mail.fetch(num, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])
        typ, data = mail.store(num, '+FLAGS', '\\Seen')
        rawmessage.append(msg)

    for message in rawmessage:
        header = email.header.make_header(email.header.decode_header(message['Subject']))
        subject = str(header)
        sender = message['From'].split()[-1][1:-1]
        payload = [m.get_payload() for m in message.get_payload()][0]
        member = Member.objects.filter(email=sender)
        print("Updating preferences for: " + message['From'])
        if len(member) != 0:
            member = member[0]
            if subject == 'AUTHOR':
                body = payload.split('\n')
                for line in body:
                    print(line)
                    line = line.split(',')
                    if len(line) == 2:
                        if '@' in line[0]:
                            author = Author.objects.filter(email=line[0])
                        else:
                            author = Author.objects.filter(name=line[0])

                        arating = []
                        if len(author) != 0:
                            author = author[0]
                            arating = AuthorRating.objects.filter(member=member, author=author)
                            arating.rating = int(line[1])
                            arating.save()
                        else:
                            author = Author(name=line[0])
                            author.save()

                        if len(arating) != 0:
                            arating = arating[0]
                            arating.rating = int(line[1])
                        else:
                            arating = AuthorRating(member=member, author=author, rating=int(line[1]))

                        arating.save()

            elif subject == 'ARTICLE':
                body = message.get_body()
                body = body.split('\n')
                for line in body:
                    line = line.split(',')
                    if len(line) == 2:
                        article = Article.objects.filter(shortid=line[0])[0]

                        if len(article) != 0:
                            arating = ArticleRating.objects.filter(member=member, article=article)
                            if len(arating) != 0:
                                arating = arating[0]
                                arating.rating = int(line[1])
                            else:
                                arating = ArticleRating(member=member, article=article, rating=int(line[1]))
                            arating.save()
    mail.close()

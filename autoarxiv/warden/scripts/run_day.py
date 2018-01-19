import sys
import time
from datetime import datetime

"""

"""


class ModelRunner:

    def __init__(self):

        updated = False
        fetched = False

        while True:
            now = datetime.now().strftime('%H%M')

            if updated == False:
                print('updating emails')
                updated = True

            # This part does the new article fetching
            if ('0500' <= now <= '0630' and fetched == True):

            if ('0630' <= now <= '0700' and fetched == False):



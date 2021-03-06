import requests
import sys
import multiprocessing
import time
from bs4 import BeautifulSoup

class Spider:

    def __init__(self, domain='https://www.example.com', start_url='/', exclusive=False, processes=2, quiet=False):

        self.domain = domain
        self.start_url = start_url
        self.exclusive = exclusive
        self.processes = processes
        self.in_q = multiprocessing.Manager().Queue()
        self.out_q = multiprocessing.Manager().Queue()
        self.processed = set()
        self.quiet = quiet

    def get_links(self, link):

        response = requests.get(link, timeout=15)
        html = response.text

        if response.status_code != 200:
            raise Exception('got http error response ' + str(response.status_code))

        s = BeautifulSoup(html, 'html.parser')

        links = [ a.get('href') for a in s.find_all('a') ]

        tmp = []
        for link in links:
            if link != None:
                if self.exclusive == True:
                    # exclude any links not relative to given domain
                    if 'http' not in link:
                        tmp.append(link)
                else:
                    tmp.append(link)
        links = tmp

        return links

    def _worker(self):

        if self.in_q.qsize() == 0:
            time.sleep(2)

        while self.in_q.qsize() > 0:

            link = self.in_q.get()
            link = link.strip()

            if not self.quiet:
                print(link)
                sys.stdout.flush()

            if link in self.processed:
                continue

            self.processed.add(link)

            # complete relative links
            if 'http' not in link:
                link = self.domain + link

            try:
                links = self.get_links(link)
            except Exception as e:
                self.out_q.put({link: str(e)})

            self.out_q.put({link: links})

            for link in links:
                self.in_q.put(link)

        return

    def crawl(self):

        start_url = self.domain + self.start_url

        self.in_q.put(start_url)

        p = multiprocessing.Pool(self.processes)
        p.apply_async(self._worker)

        p.close()
        p.join()

        results = []
        while self.out_q.qsize() > 0:
            results.append(self.out_q.get())

        return results

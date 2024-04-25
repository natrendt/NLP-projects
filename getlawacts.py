#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Mar  8 17:31:17 2024

@author: Jan Daciuk
"""
from bs4 import BeautifulSoup
import urllib
import urllib.request
import regex
import wget
from datetime import date
import time
import json

acts_per_page = 50


def get_page_boundaries(base):
    """
    Get the number and date for the first and last law act in the year.

    Parameters
    ----------
    base : str
        Base URL that includes the year.

    Returns
    -------
    A tuple containing:
        - lowest law act number on the page,
        - earlierst date of a law act on the page,
        - highest act law number on the page,
        - latest date of a law act on the page.
    """
    url = base
    with urllib.request.urlopen(url) as fp:
        soup = BeautifulSoup(fp, "html.parser")
        d1 = soup.find("div", id="content", recursive=True)
        d2 = d1.find("div", id="d_content")
        t1 = d2.find("table", id="c_table")
        t2 = t1.find("tbody")
        highest = 0
        lowest = highest
        for t3 in t2.find_all("tr"):
            if "class" in t3.attrs and t3["class"] == ["noBorder"]:
                continue
            col = 0     # column number
            for t4 in t3.find_all("td"):
                col += 1
                if col == 1:
                    # Act number column
                    act_no = int(t4.a.text)
                    lowest = act_no
                    if act_no > highest:
                        highest = act_no
                elif col == 4:
                    # Date column
                    first_date = t4.text
                    if act_no == highest:
                        last_date = first_date
        return (lowest, date.fromisoformat(first_date.strip()),
                highest, date.fromisoformat(last_date.strip()))


def get_starting_page(start_url, searched_date, ascending):
    """
    Get the page number where downloading of law acts should start.

    Parameters
    ----------
    start_url : str
        URL for all acts from the specified year.
    searched_date : date
        Date of act laws from which downloading should start.
    ascending : Boolean
        Whether to download later (True) or earlier (False) law acts.

    Returns
    -------
    middle : int
        Page number on which the first/last law act is located.
    pages : int
        Number of pages for the year.

    """
    # See what the range of dates and number oc acts for the whole year is
    start_url += f"/{searched_date.year}"
    start_no, start_date, _, _ = get_page_boundaries(start_url + "/1")
    _, _, end_no, end_date = get_page_boundaries(start_url)
    pages = (end_no // acts_per_page) + 1
    today = date.today()
    max_month = 12
    if searched_date.year == today.year:
        max_month = today.month
    pages_per_month = pages // max_month
    # Try to guess the right page and search around it
    current_page = searched_date.month * pages_per_month
    lower = max((searched_date.month - 2) * pages_per_month, 1)
    upper = min((searched_date.month + 2) * pages_per_month, pages)
    # Verify boundaries
    _, lower_date, _, _ = get_page_boundaries(f"{start_url}/{lower}")
    _, _, _, upper_date = get_page_boundaries(f"{start_url}/{upper}")
    while lower > 1 and lower_date > searched_date:
        lower -= 1
        _, lower_date = get_page_boundaries(f"{start_url}/{lower}")
    while upper < pages and upper_date < searched_date:
        upper += 1
        _, _, _, upper_date = get_page_boundaries(f"{start_url}/{upper}")
    # Binary search for the proper page
    middle = current_page
    fs = f"{start_url}/{middle}"
    _, l_date, _, u_date = get_page_boundaries(fs)
    while (lower <= upper
           and (searched_date < l_date or searched_date > u_date)):
        if searched_date < l_date:
            upper = middle - 1
        elif searched_date > u_date:
            lower = middle + 1
        else:
            break
        middle = min(max((lower + upper) // 2, 1), pages)
        fs = f"{start_url}/{middle}"
        _, l_date, _, u_date = get_page_boundaries(fs)
    # Look at which page exactly the date starts/ends
    if ascending:
        if l_date == searched_date and middle > 1:
            lower = middle - 1
            fs = f"{start_url}/{lower}"
            _, l_date, _, u_date = get_page_boundaries(fs)
            while l_date == searched_date and lower > 1:
                middle = lower
                lower -= 1
                _, l_date, _, u_date = get_page_boundaries(fs)
            if u_date == searched_date:
                middle = lower
    else:  # descending
        if u_date == searched_date and middle < pages:
            upper = middle + 1
            fs = f"{start_url}/{upper}"
            _, l_date, _, u_date = get_page_boundaries(fs)
            while u_date == searched_date and upper < pages:
                middle = upper
                upper += 1
                _, l_date, _, u_date = get_page_boundaries(fs)
            if l_date == searched_date:
                middle = upper
    return middle, pages


def get_page(page_url):
    with urllib.request.urlopen(page_url) as fp:
        soup = BeautifulSoup(fp, "html.parser")
        d1 = soup.find("div", id="content", recursive=True)
        d2 = d1.find("div", id="d_content")
        t1 = d2.find("table", id="c_table")
        t2 = t1.find("tbody")
        result = []
        for t3 in t2.find_all("tr"):
            # Ignore headers
            if "class" in t3.attrs and t3["class"] == "noBorder":
                continue
            col = 0     # column number
            for t4 in t3.find_all("td"):
                col += 1
                if col == 2:
                    # Law act name
                    a1 = t4.find("a")
                    # Normalize text by removing carriage returns
                    # and double spaces
                    act_name = regex.sub(r"\s+", " ", a1.text).strip()
                elif col == 3:
                    # Act PDF link
                    a1 = t4.find("a")
                    act_link = a1["href"]
                elif col == 4:
                    # Date column
                    act_date = date.fromisoformat(t4.text.strip())
                    result.append([act_link, act_date, act_name])
        return result


def download_page(page, delay, ddir, verbose, act_no):
    """
    Download files from the given page list to the given directory.

    Parameters
    ----------
    page : list
        A list of lists: (url, publication date, title).
    delay : int
        Wait that many seconds between downloads.
    ddir : str
        Directory to store downloaded files.
    act_no : int
        If 0, print nothing, otherwise print downloaded act number,
        its file name, and the act title.

    Returns
    -------
    None.

    """
    hprefix = "https://dziennikustaw.gov.pl"
    for u in page:
        fname = u[0].split('/')[-1]
        if act_no != 0:
            print(f"Downloading {act_no}. {fname}, {u[1]}, {u[2]}")
            act_no += 1
        wget.download(hprefix + u[0], ddir + "/" + fname)
        time.sleep(delay)


def download_acts(start_url, page, searched_date, number, pages, ascending,
                  delay, ddir, verbose):
    """
    Download "number" law acts from searched_date on.

    Parameters
    ----------
    start_url : str
        URL prefix of web pages with links to law acts.
    page : int
        Page number for law acts published in a given year on a searched_date.
    searched_date : date
        Date of the first or last law act to be downloaded.
    number : int
        number of law acts to be downloaded.
    pages : int
        Number of pages in a given searched_date.year.
    ascending : Boolean
        If True, download law acts on and later than the searched_date.
        If False, download law acts on and earlier than the searched_date.
    delay : int
        Wait that many seconds between downloads.
    ddir : str
        Directory to store downloaded files.
    verbose : bool
        If True, print names of downloaded files.

    Returns
    -------
    whole_list : TYPE
        DESCRIPTION.

    """
    year = searched_date.year
    url = f"{start_url}/{year}/{page}"
    to_be_downloaded = number
    whole_list = []
    ex = (lambda x: [x[0].split("/")[-1], x[2]])  # file name and act name
    if verbose:
        # Set the first act number when printing
        act_no = 1
    else:
        # Do not print information about downloaded acts
        act_no = 0
    act_list = get_page(url)
    if ascending:
        # If ascending, we are looking for the first act on the page
        # that has the date not earlier than the searched one.
        def mycmp(a, b): return a >= b
        # For subsequent acts go upwards in page numbers
        m = 1
        # As the web page is in reverse order, reverse it once again.
        act_list = act_list[::-1]
    else:
        # If descending, we are looking for the last act on the page
        # that has the date not later than the searched one.
        # As the web page is in reverse order, search from the start.
        def mycmp(a, b): return a <= b
        # For subsequent acts go downwards in pge numbers
        m = -1
    for i in range(acts_per_page):
        if mycmp(act_list[i][1], searched_date):
            break
    d = acts_per_page
    if acts_per_page - i > number:
        d = number + i
    download_page(act_list[i:d], delay, ddir, verbose, act_no)
    whole_list += map(ex, act_list[i:d])
    to_be_downloaded -= len(act_list) - i
    if act_no > 0:
        act_no += len(act_list) - i
    while to_be_downloaded > 0:
        page += m
        if page <= 0 or page > pages:
            # Move to the previous or next year
            year += m
            end_no, _, _, _ = get_page_boundaries(start_url)
            pages = (end_no // acts_per_page) + 1
            if page <= 0:
                # Previous year
                page = pages
            else:
                # Next year
                page = 1
        url = f"{start_url}/{year}/{page}"
        act_list = get_page(url)
        if m == -1:
            act_list = act_list[::-1]
        download_page(act_list[0:min(acts_per_page, to_be_downloaded)],
                      delay, ddir, verbose, act_no)
        whole_list += map(ex, act_list[0:min(acts_per_page,
                                             to_be_downloaded)])
        to_be_downloaded -= acts_per_page
        if act_no > 0:
            act_no += acts_per_page
    return whole_list


def get_law_acts(year, month, day, number, delay, ascending=True, ddir="Data",
                 verbose=True):
    """
    Download a number of law acts from Rządowe Centrum Legislacji.
    Start from the specified date, and procede to subsequent dates
    if ascending is True. Otherwise, download acts from earlier dates.
    Stop when the specified number of law acts is download or there are
    no more acts to dowload.

    Parameters
    ----------
    year : int
        Year to start with.
    month : int
        Month to start with.
    day : int
        Day to start with.
    number : int
        How many law acts to download.
    delay : int
        Wait the specied number of seconds before download another act.
    ascending : BOOLEAN, optional
        Whether to download acts later than the date. The default is True.
    ddir : str, optional
        Directory to dowload the acts. The default is ".".
    verbose: bool
        If True, print downloaded file names.

    Returns
    -------
    A list of downloaded law acts, with file name and title for each act.

    """
    start_url = "https://dziennikustaw.gov.pl/DU/rok"
    searched_date = date(year, month, day)
    starting_page, pages = get_starting_page(start_url, searched_date,
                                             ascending)
    dl = download_acts(start_url, starting_page, searched_date, number, pages,
                       ascending, delay, ddir, verbose)
    json.dump(dl, fp=open(f"{ddir}/downloaded_acts.json", "w"))
    for f in dl:
        print(f"Downloaded {f[0]} --- {f[1]}")
    return dl


if __name__ == "__main__":
    import argparse
    today = date.today()
    default_end_date = f"{today.day:02}.{today.month:02}.{today.year:04}"
    parser = argparse.ArgumentParser(description="Get legal acts.")
    parser.add_argument("-s", "--start_date", type=str,
                        help="Starting date dd.mm.yyyy")
    parser.add_argument("-e", "--end_date", type=str,
                        help="Ending date dd.mm.yyyy",
                        default=default_end_date)
    parser.add_argument("-n", "--number",
                        default=100, type=int,
                        help="Number of acts to download")
    parser.add_argument("-d", "--delay",
                        default=3, type=int)
    parser.add_argument("-f", "--folder", type=str, default="Data",
                        help="Directory to store data.")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print what the programs is doing.")
    args = parser.parse_args()
    if "start_date" in args and args.start_date is not None:
        the_date = args.start_date
        asc = True
    else:
        the_date = args.end_date
        asc = False
    date_list = the_date.split(".")
    if len(date_list[0]) == 1:
        date_list[0] = '0' + date_list[0]
    get_law_acts(int(date_list[2]), int(date_list[1]), int(date_list[0]),
                 args.number, args.delay, asc, args.folder, args.verbose)

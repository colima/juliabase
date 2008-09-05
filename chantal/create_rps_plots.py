#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
import glob, gzip, re, datetime, math, pickle, os
import matplotlib, matplotlib.numerix
matplotlib.use("Agg")
import pylab

binning = 60
number_of_slots = 24*3600//binning

now = datetime.datetime.now()

apache_date_pattern = re.compile(ur".*\[(?P<date>[:/0-9a-zA-Z]+) [+0-9]+\]")
def read_times_apache():
    times = number_of_slots * [0]
    for filename in glob.glob("/var/log/apache2/access.log*"):
        if filename.endswith(".gz"):
            logfile = gzip.open(filename)
        else:
            logfile = open(filename)
        for line in logfile:
            date = apache_date_pattern.match(line).group("date")
            timestamp = datetime.datetime.strptime(date, "%d/%b/%Y:%H:%M:%S")
            timedelta = now - timestamp
            if datetime.timedelta(0) < timedelta < datetime.timedelta(1):
                times[(24*3600 - timedelta.seconds)//binning] += 1
        logfile.close()
    return times

mysql_date_pattern = re.compile(ur"^\d{6} (\d| )\d:\d\d:\d\d")
db_hit_pattern = re.compile(ur"(\d{6} (\d| )\d:\d\d:\d\d)?\s+\d+ Query\s+(SELECT|DELETE|INSERT|ALTER|CREATE|UPDATE|SHOW)")
def read_times_mysql():
    times = number_of_slots * [0]
    for filename in glob.glob("/var/log/mysql/mysql.log*"):
        if filename.endswith(".gz"):
            logfile = gzip.open(filename)
        else:
            logfile = open(filename)
        timedelta = datetime.timedelta(0)
        for line in logfile:
            date_match = mysql_date_pattern.match(line)
            if date_match:
                date = date_match.group()
                if date[7] == " ":
                    date = date[:7] + "0" + date[8:]
                timestamp = datetime.datetime.strptime(date, "%y%m%d %H:%M:%S")
                timedelta = now - timestamp
            if datetime.timedelta(0) < timedelta < datetime.timedelta(1) and db_hit_pattern.match(line):
                times[(24*3600 - timedelta.seconds)//binning] += 1
        logfile.close()
    return times

window_half_width = 5*60//binning
def mollifier(x):
    if -window_half_width < x < window_half_width:
        return 2.252283621/window_half_width * math.exp(-1/(1-(x/window_half_width)**2))
    else:
        return 0

def calculate_rps(times):
    rps = []
    for i in range(number_of_slots):
        integral = 0
        for j in range(i-window_half_width, i+window_half_width+1):
            if 0 <= j < number_of_slots:
                integral += times[j] * mollifier(i - j)
        rps.append(integral/binning)
    return rps

def get_load_avgs(filename):
    def timedelta_to_seconds(timedelta):
        return timedelta.days*3600*24 + timedelta.seconds + timedelta.microseconds*1e-6
    try:
        load_avgs = pickle.load(open(filename, "rb"))
    except IOError:
        load_avgs = []
    load_avgs.append((now, os.getloadavg()[2]))
    while load_avgs and now - load_avgs[0][0] > datetime.timedelta(1):
        del load_avgs[0]
    pickle.dump(load_avgs, open(filename, "wb"))
    if len(load_avgs) <= 1:
        return number_of_slots * [0]
    y_values = []
    for i in range(number_of_slots):
        timestamp = now + datetime.timedelta(-1 + i/number_of_slots)
        j = 0
        while j < len(load_avgs) and load_avgs[j][0] < timestamp:
            j += 1
        assert j < len(load_avgs)
        if j == 0:
            y_values.append(0)
        else:
            y_values.append(timedelta_to_seconds(timestamp - load_avgs[j-1][0]) /
                            timedelta_to_seconds(load_avgs[j][0] - load_avgs[j-1][0]) *
                            (load_avgs[j][1] - load_avgs[j-1][1]) + load_avgs[j-1][1])
    return y_values

x_values = matplotlib.numerix.arange(0, 24, 24/number_of_slots)

rps_apache = calculate_rps(read_times_apache())
pylab.subplot(311)
pylab.plot(x_values, rps_apache, color="#800000")
pylab.title(u"Apache server load")
pylab.ylabel(u"requests/sec")
pylab.xlim(0,24)
pylab.xticks(matplotlib.numerix.arange(1-now.minute/60 + (now.hour+1)%2, 25, 2), 100*[u""])

pylab.subplot(312)
rps_mysql = calculate_rps(read_times_mysql())
pylab.plot(x_values, rps_mysql, color="b")
pylab.title(u"MySQL server load")
pylab.xticks(matplotlib.numerix.arange(1-now.minute/60 + (now.hour+1)%2, 25, 2), 100*[u""])
pylab.xlim(0,24)
pylab.ylabel(u"queries/sec")

pylab.subplot(313)
load_avgs = get_load_avgs("/home/bronger/repos/chantal/online/load_avgs.pickle")
pylab.plot(x_values, load_avgs, color="k")
pylab.title(u"CPU load")
pylab.xticks(matplotlib.numerix.arange(1-now.minute/60 + (now.hour+1)%2, 25, 2),
             [str(i%24) for i in range((now.hour-23+(now.hour+1)%2)%24, 100, 2)])
pylab.xlim(0,24)
pylab.ylabel(u"load average 15")
pylab.xlabel(u"time")

pylab.savefig(open("/home/bronger/repos/chantal/online/chantal/media/server_load.png", "wb"),
              facecolor=("#e6e6e6"), edgecolor=("#e6e6e6"))

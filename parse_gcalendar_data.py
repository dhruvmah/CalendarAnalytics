from icalendar import Calendar, Event
from collections import Counter
from datetime import timedelta, time
import datetime
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

class CalendarParser(object):
	def __init__(self, ics_file, start_date, end_date):
		self.ics_file = ics_file
		self.g = open(self.ics_file,'rb')
		self.gcal = Calendar.from_ical(self.g.read())
		self.start_date = start_date
		self.end_date = end_date
	def parse_avg_meeting_length(self):
		avg_hours = []
		for component in self.gcal.walk():
			if component.name == "VEVENT":
				try:
					meeting_date = component.get('DTSTART').dt.date()
					start_dt = component.get('DTSTART').dt
					end_dt = component.get('dtend').dt
					if (meeting_date >= self.start_date and meeting_date <= self.end_date):
						hours_difference = abs(start_dt - end_dt).total_seconds() / 3600.0
						avg_hours.append(hours_difference)
				except:
					continue
		print "Total number of meetings: " + str(len(avg_hours))
		print "Average length of meetings: " + str(np.mean(avg_hours)) + " hours"
	def parse_num_meetings_per_day(self):
		days = []
		for component in self.gcal.walk():
			if component.name == "VEVENT":
				try:
					meeting_date = component.get('DTSTART').dt.date()
					start_dt = component.get('DTSTART').to_ical()
					if (meeting_date >= self.start_date and meeting_date <= self.end_date):
						days.append(start_dt.split("T")[0])
				except:
					continue
		days_counter = Counter(days)
		num_meetings_day = np.mean(days_counter.values())
		print "Average number of meetings per day: " + str(num_meetings_day)
		print "Average number of meetings per week: " + str(num_meetings_day*7)
	def parse_percent_time_in_meetings(self, num_hours_week, start_d_obj, end_d_obj):
		meeting_hours = []
		monday1 = (start_d_obj - timedelta(days=start_d_obj.weekday()))
		monday2 = (end_d_obj - timedelta(days=end_d_obj.weekday()))
		num_weeks_worked = (monday2 - monday1).days / 7
		for component in self.gcal.walk():
			if component.name == "VEVENT":
				try:
					meeting_date = component.get('DTSTART').dt.date()
					start_dt = component.get('DTSTART').dt
					end_dt = component.get('dtend').dt
					if (meeting_date >= self.start_date and meeting_date <= self.end_date):
						hours_difference = abs(start_dt - end_dt).total_seconds() / 3600.0
						if (hours_difference > 3):
							continue
						meeting_hours.append(hours_difference)
				except:
					continue
		perc_time_meetings = np.sum(meeting_hours) / (num_hours_week * num_weeks_worked)
		print "Percentage of time spent in meetings: " + str(perc_time_meetings)
	def parse_meeting_size(self):
		num_people_meeting = []
		for component in self.gcal.walk():
			if component.name == "VEVENT":
				try:
					meeting_date = component.get('DTSTART').dt.date()
					start_dt = component.get('DTSTART').dt
					if (meeting_date >= self.start_date and meeting_date <= self.end_date):
						attendees = component.get('ATTENDEE')
						num_people_meeting.append(len(attendees))
				except:
					continue
		print "Average number of people attending your meetings: " + str(np.mean(num_people_meeting))
	def parse_one_on_ones_with_manager(self, manager_email, personal_email):
		one_on_ones = []
		for component in self.gcal.walk():
			if component.name == "VEVENT":
				try:
					meeting_date = component.get('DTSTART').dt.date()
					start_dt = component.get('DTSTART').dt
					organizer = component.get('ORGANIZER').split(":")[1]
					attendee = component.get('ATTENDEE')[0].split(":")[1]
					if (meeting_date >= self.start_date and meeting_date <= self.end_date):
						if ((organizer == manager_email) or (organizer==personal_email)) \
						and ((attendee == personal_email) or (attendee == manager_email)):
							one_on_ones.append(component.get("SUMMARY"))
				except:
					continue
		print "Number of one on one meetings: " + str(len(one_on_ones))
	def parse_one_on_ones(self):
		one_on_ones = []
		for component in self.gcal.walk():
			if component.name == "VEVENT":
				try:
					meeting_date = component.get('DTSTART').dt.date()
					start_dt = component.get('DTSTART').dt
					organizer = component.get('ORGANIZER').split(":")[1]
					attendee = component.get('ATTENDEE')[0].split(":")[1]
					if (meeting_date >= self.start_date and meeting_date <= self.end_date):
						attendees = component.get('ATTENDEE')
						if (len(attendees) == 2):
							one_on_ones.append(component.get("SUMMARY"))
				except:
					continue
		print "Number of one on one meetings: " + str(len(one_on_ones))
	def parse_non_work_hour_meetings(self, start_time, end_time):
		non_work_hour_meetings = []
		total_meetings = []
		for component in self.gcal.walk():
			if component.name == "VEVENT":
				try:
					meeting_date = component.get('DTSTART').dt.date()
					start_dt = component.get('DTSTART').dt
					if (meeting_date >= self.start_date and meeting_date <= self.end_date):
						meeting_time = time(start_dt.timetuple().tm_hour, start_dt.timetuple().tm_min)
						total_meetings.append(component.get('SUMMARY'))
						if (meeting_time < start_time) or (meeting_time > end_time):
							non_work_hour_meetings.append(component.get('SUMMARY'))
				except:
					continue
		print "Number of non work hour meetings: " + str(len(non_work_hour_meetings))
		print "Percentage of meetings not in work hours: " + str(len(non_work_hour_meetings)/float(len(total_meetings)))
	def parse_calendar_fragmentation(self):
		days = []
		for component in self.gcal.walk():
			if component.name == "VEVENT":
				try:
					start_dt = component.get('dtstart')
					days.append(start_dt.to_ical().split("T")[0])
				except:
					continue
		meeting_gaps = {key: [] for key in np.unique(days)}
		for component in self.gcal.walk():
			if component.name == "VEVENT":
				start_dt = component.get('dtstart')
				start_time = start_dt.dt
				day = start_dt.to_ical().split("T")[0]
				meeting_gaps[day].append(start_time)
		start_diffs = []
		for i in range(len(meeting_gaps.values())):
			meeting_start_times = meeting_gaps.values()[i]
			if len(meeting_start_times) > 1:
				time_deltas = []
				try:
					for j in range(1,len(meeting_start_times),1):
						delta = meeting_start_times[j]-meeting_start_times[j-1]
						time_deltas.append(delta.total_seconds() // 3600)
				except:
					continue
				start_diff = np.mean(np.abs(time_deltas))
				start_diffs.append(start_diff)
		print "Average gap between meetings on a given day: " + str(np.mean(start_diffs)) + " hours"

def create_calendar_network(ics_file, personal_email, start_date, end_date):
	ics_file = ics_file
	g = open(ics_file,'rb')
	gcal = Calendar.from_ical(g.read())
	G=nx.Graph()
	G.add_node(personal_email)
	for component in gcal.walk():
		if component.name == "VEVENT":
			try:
				organizer = component.get('ORGANIZER').split(":")[1]
				attendees = component.get('ATTENDEE')
				date = component.get('DTSTART').dt.date()
				if (date >= start_date and date <= end_date):
					if (personal_email != organizer):
						G.add_edge(personal_email,organizer,weight=1.0)
					for attendee in attendees:
						attendee_email = attendee.split(":")[1]
						if (personal_email != attendee_email):
							G.add_edge(personal_email, attendee_email,weight=1.0)
			except:
				continue
	for component in gcal.walk():
		if component.name == "VEVENT":
			try:
				organizer = component.get('ORGANIZER').split(":")[1]
				attendees = component.get('ATTENDEE')
				meeting_size = len(attendees) + 1
				date = component.get('DTSTART').dt.date()
				if (date >= start_date and date <= end_date):
					if (personal_email != organizer):
						G[personal_email][organizer]["weight"] += (1.0 / meeting_size)
					for attendee in attendees:
						attendee_email = attendee.split(":")[1]
						if (personal_email != attendee_email):
							G[personal_email][attendee_email]["weight"] += (1.0 / meeting_size)
			except:
				continue
	out_file = open("rzhang_connection_graph.txt","wb")
	out_file.write("User\tConnection Strength\n")
	for key in sorted(G[personal_email], key=G[personal_email].get, reverse=True):
		out_file.write(key + "\t" + str(G[personal_email][key]["weight"]))
		out_file.write("\n")

def run_basic_parser():
	parser = CalendarParser("rzhang@identifiedtech.com.ics",datetime.date(2014,1,1),datetime.date(2017,7,12))
	parser.parse_avg_meeting_length()
	parser.parse_num_meetings_per_day()
	parser.parse_percent_time_in_meetings(45, datetime.date(2014,1,1),datetime.date(2017,7,12))
	parser.parse_meeting_size()
	parser.parse_one_on_ones()
	parser.parse_non_work_hour_meetings(time(9,0),time(18,0))
	parser.parse_calendar_fragmentation()

#create_calendar_network("rzhang@identifiedtech.com.ics","rzhang@identifiedtech.com",datetime.date(2014,1,1),datetime.date(2017,7,12))
run_basic_parser()


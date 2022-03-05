import re
from copy import deepcopy
from datetime import date, datetime, time
from typing import Dict, List, Optional
from uuid import UUID
from xml.etree import ElementTree

import bs4
import requests
from pydantic import BaseModel

from sessionize import Event, Room, Session, Speaker
from util import pentabarf_format_duration


class DevConfSession(BaseModel):
    id: int
    title: str
    description: str
    room: str
    starts_at: datetime
    ends_at: datetime
    speakers: List[str]


class DevConfEvent(BaseModel):
    location: str
    venue: str
    sessions: List[DevConfSession]


def get_events(event: Event) -> List[DevConfEvent]:
    events: List[DevConfEvent] = []
    sessions_by_id = {session.id: session for session in event.sessions}
    speakers_by_id = {speaker.id: speaker for speaker in event.speakers}

    for location, short_location, day in [
        ("Cape Town", "capetown", date(2022, 4, 5)),
        ("Virtual", "virtual", date(2022, 4, 7)),
        ("Johannesburg", "joburg", date(2022, 4, 7)),
    ]:
        response = requests.get(f"https://devconf.co.za/{short_location}")
        soup = bs4.BeautifulSoup(response.text, "html.parser")
        events.append(parse_agenda(soup, sessions_by_id, speakers_by_id, location, day))

    return events


def parse_agenda(
    soup: bs4.BeautifulSoup,
    sessions_by_id: Dict[int, Session],
    speakers_by_id: Dict[UUID, Speaker],
    location: str,
    day: date,
) -> DevConfEvent:
    sessions: List[DevConfSession] = []
    venue = soup.find("div", class_="sponsor-content-detail-location").find("a")
    agenda = soup.find_all("div", class_="agenda")[1]

    agenda_rows = agenda.find_all("div", class_=re.compile("^agenda-row-.*"))
    for i, row in enumerate(agenda_rows):
        s = parse_agenda_row(row, sessions_by_id, speakers_by_id, i, day)
        if not s:
            continue
        sessions.append(s)

    end_times = {session.starts_at: session.ends_at for session in sessions}

    agenda_sessions = agenda.find_all("div", class_="agenda-session")
    for session in agenda_sessions:
        if not session.contents:
            continue

        s = parse_agenda_session(
            session, sessions_by_id, speakers_by_id, day, end_times
        )
        if not s:
            continue
        sessions.append(s)

    return DevConfEvent(
        location=location,
        venue=venue.text if venue else "",
        sessions=sessions,
    )


def parse_agenda_row(
    soup: bs4.BeautifulSoup,
    sessions_by_id: Dict[int, Session],
    speakers_by_id: Dict[UUID, Speaker],
    _id: int,
    day: date,
) -> Optional[DevConfSession]:
    m = re.match(r"\s*(\d\dh\d\d) → (.*) ← (\d\dh\d\d)\s*", soup.text)
    if not m:
        return None

    starts_at, title, ends_at = m.groups()
    starts_at = datetime.combine(day, parse_time(starts_at))
    ends_at = datetime.combine(day, parse_time(ends_at))

    if "agenda-row-style-keynote" in soup["class"]:
        # Keynote session row requires special handling
        return parse_keynote_row(
            soup, sessions_by_id, speakers_by_id, starts_at, ends_at
        )
    else:
        return DevConfSession(
            id=_id,
            title=title,
            description="",
            room="Other",
            starts_at=starts_at,
            ends_at=ends_at,
            speakers=[],
        )


def parse_keynote_row(
    soup: bs4.BeautifulSoup,
    sessions_by_id: Dict[int, Session],
    speakers_by_id: Dict[UUID, Speaker],
    starts_at: datetime,
    ends_at: datetime,
) -> DevConfSession:
    keynote = soup.find("div", class_="agenda-keynote-session")
    _id = int(keynote["data-slot-id"])
    session = sessions_by_id[_id]
    speakers = [speakers_by_id[i].fullName for i in session.speakers]
    return DevConfSession(
        id=_id,
        title=session.title,
        description=session.description,
        room="Other",
        starts_at=starts_at,
        ends_at=ends_at,
        speakers=speakers,
    )


def parse_agenda_session(
    soup: bs4.BeautifulSoup,
    sessions_by_id: Dict[int, Session],
    speakers_by_id: Dict[UUID, Speaker],
    day: date,
    end_times: Dict[datetime, datetime],
) -> Optional[DevConfSession]:
    _id = int(soup["data-slot-id"])
    room = soup.find("div", class_="agenda-session-room").text.strip()
    starts_at = soup.find("div", class_="agenda-session-time").text.strip()

    if _id not in sessions_by_id:
        return None
    session = sessions_by_id[_id]

    starts_at = datetime.combine(day, parse_time(starts_at))
    ends_at = end_times[starts_at]

    speakers = [speakers_by_id[i].fullName for i in session.speakers]

    return DevConfSession(
        id=_id,
        title=session.title,
        description=session.description,
        room=room,
        starts_at=starts_at,
        ends_at=ends_at,
        speakers=speakers,
    )


def parse_time(t: str) -> time:
    t = t.strip()
    if not re.fullmatch(r"\d\dh\d\d", t):
        raise ValueError("invalid time format")
    return time(int(t[:2]), int(t[3:]))


def event_to_pentabarf(event: DevConfEvent):
    rooms = {session.room for session in event.sessions}
    days = {session.starts_at.date() for session in event.sessions}
    year = event.sessions[0].starts_at.year

    root = ElementTree.Element("schedule")
    conference = ElementTree.SubElement(root, "conference")
    ElementTree.SubElement(
        conference, "title"
    ).text = f"DevConf {event.location} {year}"
    ElementTree.SubElement(conference, "city").text = event.location
    if event.venue:
        ElementTree.SubElement(conference, "venue").text = event.venue

    for i, d in enumerate(sorted(days)):
        day = ElementTree.SubElement(
            root, "day", attrib={"index": str(i + 1), "date": d.strftime("%Y-%m-%d")}
        )

        for r in sorted(rooms):
            room = ElementTree.SubElement(day, "room", attrib={"name": r})

            for session in event.sessions:
                if session.starts_at.date() != d:
                    continue
                if session.room != r:
                    continue

                e = ElementTree.SubElement(
                    room, "event", attrib={"id": str(session.id)}
                )
                ElementTree.SubElement(e, "start").text = session.starts_at.strftime(
                    "%H:%M"
                )
                ElementTree.SubElement(e, "duration").text = pentabarf_format_duration(
                    session.starts_at, session.ends_at
                )
                ElementTree.SubElement(e, "room").text = r
                ElementTree.SubElement(e, "title").text = session.title
                ElementTree.SubElement(e, "description").text = session.description
                ElementTree.SubElement(e, "language")

                persons = ElementTree.SubElement(e, "persons")
                for speaker in session.speakers:
                    ElementTree.SubElement(persons, "person").text = speaker

    ElementTree.indent(root, space="\t", level=0)
    return ElementTree.tostring(root, encoding="unicode")

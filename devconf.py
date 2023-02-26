import re
from datetime import date, datetime, time
from typing import Dict, List, Optional
from uuid import UUID

import bs4
import requests
from pydantic import BaseModel

import pentabarf
import sessionize


class EventConfig(BaseModel):
    name: str
    short_name: str
    day: date


class Config(BaseModel):
    sessionize_id: str
    use_archive: bool
    events: List[EventConfig]


class Session(BaseModel):
    id: int
    title: str
    description: str
    room: str
    starts_at: datetime
    ends_at: datetime
    speakers: List[str]


class Event(BaseModel):
    location: str
    venue: str
    sessions: List[Session]
    starts_at: datetime
    ends_at: datetime


def get_event(
    event: sessionize.Event, event_config: EventConfig, use_archive: bool
) -> Event:
    sessions_by_id = {session.id: session for session in event.sessions}
    speakers_by_id = {speaker.id: speaker for speaker in event.speakers}

    if use_archive:
        archive_datetime = event_config.day.strftime("%Y%m%d000000")
        response = requests.get(
            f"https://web.archive.org/web/{archive_datetime}/https://devconf.co.za/{event_config.short_name}"
        )
    else:
        response = requests.get(f"https://devconf.co.za/{event_config.short_name}")

    soup = bs4.BeautifulSoup(response.text, "html.parser")
    return parse_agenda(
        soup, sessions_by_id, speakers_by_id, event_config.name, event_config.day
    )


def parse_agenda(
    soup: bs4.BeautifulSoup,
    sessions_by_id: Dict[int, sessionize.Session],
    speakers_by_id: Dict[UUID, sessionize.Speaker],
    location: str,
    day: date,
) -> Event:
    sessions: List[Session] = []

    venue = ""
    scdl = soup.find("div", class_="sponsor-content-detail-location")
    if scdl:
        venue_anchor = scdl.find("a")
        if isinstance(venue_anchor, bs4.Tag):
            venue = venue_anchor.text

    agendas = soup.find_all("div", class_="agenda")
    if not agendas:
        raise Exception("could not find agenda")
    agenda = agendas[0]

    agenda_rows = agenda.find_all("div", class_=re.compile("^agenda-row-.*"))
    for i, row in enumerate(agenda_rows):
        s = parse_agenda_row(row, sessions_by_id, speakers_by_id, i, day)
        if not s:
            continue
        sessions.append(s)

    if not sessions:
        raise Exception("could not find sessions")

    event_start = min(sessions, key=lambda s: s.starts_at).starts_at
    event_end = max(sessions, key=lambda s: s.ends_at).ends_at

    end_times = {session.starts_at: session.ends_at for session in sessions}

    agenda_sessions = agenda.find_all("div", class_="agenda-session")
    for session in agenda_sessions:
        if not session.contents:
            continue

        if "agenda-keynote-session" in session.get_attribute_list("class"):
            continue

        s = parse_agenda_session(
            session, sessions_by_id, speakers_by_id, day, end_times
        )
        if not s:
            continue
        sessions.append(s)

    return Event(
        location=location,
        venue=venue,
        sessions=sessions,
        starts_at=event_start,
        ends_at=event_end,
    )


def parse_agenda_row(
    soup: bs4.BeautifulSoup,
    sessions_by_id: Dict[int, sessionize.Session],
    speakers_by_id: Dict[UUID, sessionize.Speaker],
    _id: int,
    day: date,
) -> Optional[Session]:
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
        return Session(
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
    sessions_by_id: Dict[int, sessionize.Session],
    speakers_by_id: Dict[UUID, sessionize.Speaker],
    starts_at: datetime,
    ends_at: datetime,
) -> Session:
    keynote = soup.find("div", class_="agenda-keynote-session")
    if not isinstance(keynote, bs4.Tag):
        raise Exception("could not find keynote session ID")

    _ids = keynote.get_attribute_list("data-slot-id")
    if not _ids:
        raise Exception("could not find keynote session ID")
    _id = int(_ids[0])

    session = sessions_by_id[_id]
    speakers = [speakers_by_id[i].fullName for i in session.speakers]
    return Session(
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
    sessions_by_id: Dict[int, sessionize.Session],
    speakers_by_id: Dict[UUID, sessionize.Speaker],
    day: date,
    end_times: Dict[datetime, datetime],
) -> Optional[Session]:
    _ids = soup.get_attribute_list("data-slot-id")
    if not _ids:
        raise Exception("could not find session ID")
    _id = int(_ids[0])

    room_div = soup.find("div", class_="agenda-session-room")
    if not room_div:
        raise Exception(f"could not find room for session {_id}")
    room = room_div.text.strip()

    starts_at_div = soup.find("div", class_="agenda-session-time")
    if not starts_at_div:
        raise Exception(f"could nto find start time for session {_id}")
    starts_at = starts_at_div.text.strip()

    if _id not in sessions_by_id:
        return None
    session = sessions_by_id[_id]

    starts_at_dt = datetime.combine(day, parse_time(starts_at))
    ends_at_dt = end_times[starts_at_dt]

    speakers = [speakers_by_id[i].fullName for i in session.speakers]

    return Session(
        id=_id,
        title=session.title,
        description=session.description,
        room=room,
        starts_at=starts_at_dt,
        ends_at=ends_at_dt,
        speakers=speakers,
    )


def parse_time(t: str) -> time:
    t = t.strip()
    if not re.fullmatch(r"\d\dh\d\d", t):
        raise ValueError("invalid time format")
    return time(int(t[:2]), int(t[3:]))


def event_to_pentabarf(event: Event) -> pentabarf.Schedule:
    year = event.sessions[0].starts_at.year
    days: List[pentabarf.Day] = []

    for date in sorted({session.starts_at.date() for session in event.sessions}):
        rooms: List[pentabarf.Room] = []

        for room in sorted({session.room for session in event.sessions}):
            events: List[pentabarf.Event] = []

            for session in (s for s in event.sessions if s.room == room):
                events.append(
                    pentabarf.Event(
                        id=str(session.id),
                        title=session.title,
                        description=session.description,
                        room=room,
                        start=session.starts_at,
                        duration=session.ends_at - session.starts_at,
                        language="",
                        persons=session.speakers,
                    )
                )

            rooms.append(
                pentabarf.Room(
                    name=room,
                    events=events,
                )
            )

        days.append(
            pentabarf.Day(
                date=date,
                rooms=rooms,
            )
        )

    return pentabarf.Schedule(
        conference=pentabarf.Conference(
            title=f"DevConf {event.location} {year}",
            city=event.location,
            venue=event.venue,
            start=event.starts_at,
            end=event.ends_at,
        ),
        days=days,
    )

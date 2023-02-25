from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID
from xml.etree import ElementTree

from pydantic import BaseModel

import pentabarf
from util import xcal_format_duration


class Session(BaseModel):
    id: int
    title: str
    description: str
    startsAt: Optional[datetime]
    endsAt: Optional[datetime]
    roomId: Optional[int]
    isServiceSession: bool = False
    isPlenumSession: bool = False
    speakers: List[UUID] = []
    categoryItems: List[str] = []
    questionAnswers: List[str] = []
    liveUrl: Optional[str] = None
    recordingUrl: Optional[str] = None


class LinkType(Enum):
    Blog = "Blog"
    CompanyWebsite = "Company_Website"
    Facebook = "Facebook"
    LinkedIn = "LinkedIn"
    Sessionize = "Sessionize"
    Twitter = "Twitter"


class Link(BaseModel):
    title: str
    url: str
    linkType: LinkType


class Speaker(BaseModel):
    id: UUID
    firstName: str
    lastName: str
    bio: Optional[str]
    tagLine: Optional[str]
    profilePicture: str
    isTopSpeaker: bool
    links: List[Link]
    sessions: List[int]
    fullName: str
    categoryItems: List[str]
    questionAnswers: List[str]


class Room(BaseModel):
    id: int
    name: str
    sort: int


class Event(BaseModel):
    sessions: List[Session]
    speakers: List[Speaker]
    rooms: List[Room]
    categories: List[str]
    questions: List[str]


def event_to_pentabarf(event: Event) -> pentabarf.Schedule:
    rooms_by_id = {room.id: room for room in event.rooms}
    speakers_by_id = {speaker.id: speaker for speaker in event.speakers}
    dates = {session.startsAt.date() for session in event.sessions}
    days: List[pentabarf.Day] = []

    for d in sorted(dates):
        rooms: List[pentabarf.Room] = []

        for _, r in rooms_by_id.items():
            events: List[pentabarf.Event] = []

            for session in event.sessions:
                if session.startsAt.date() != d:
                    continue
                if session.roomId != r.id:
                    continue

                events.append(
                    pentabarf.Event(
                        id=str(session.id),
                        start=session.startsAt,
                        duration=session.endsAt - session.startsAt,
                        room=r.name,
                        title=session.title,
                        description=session.description,
                        language="",
                        persons=[speakers_by_id[s].fullName for s in session.speakers],
                    )
                )

            rooms.append(
                pentabarf.Room(
                    name=r.name,
                    events=events,
                )
            )

        days.append(
            pentabarf.Day(
                date=d,
                rooms=rooms,
            )
        )

    return pentabarf.Schedule(
        conference=pentabarf.Conference(
            title="",
            city="",
            venue="",
            start=min(dates),
            end=max(dates),
        ),
        days=days,
    )


def event_to_xcal(event: Event) -> str:
    rooms = {room.id: room for room in event.rooms}
    speakers = {speaker.id: speaker for speaker in event.speakers}

    root = ElementTree.Element(
        "iCalendar",
        attrib={
            "xmlns:xCal": "urn:ietf:params:xml:ns:xcal",
            "xmlns:pentabarf": "http://pentabarf.org",
        },
    )
    vcalendar = ElementTree.SubElement(root, "vcalendar")

    version = ElementTree.SubElement(vcalendar, "version")
    version.text = "2.0"

    for session in event.sessions:
        vevent = ElementTree.SubElement(vcalendar, "vevent")

        ElementTree.SubElement(vevent, "uid").text = str(session.id)
        ElementTree.SubElement(vevent, "dtstart").text = session.startsAt.strftime(
            "%Y%m%dT%H%M%S"
        )
        ElementTree.SubElement(vevent, "dtend").text = session.endsAt.strftime(
            "%Y%m%dT%H%M%S"
        )
        ElementTree.SubElement(vevent, "summary").text = session.title
        ElementTree.SubElement(vevent, "description").text = session.description
        ElementTree.SubElement(vevent, "location").text = rooms[session.roomId].name

        ElementTree.SubElement(vevent, "duration").text = xcal_format_duration(
            session.startsAt, session.endsAt
        )

        for speaker in session.speakers:
            ElementTree.SubElement(vevent, "attendee").text = speakers[speaker].fullName

    ElementTree.indent(root, space="\t", level=0)
    return ElementTree.tostring(root, encoding="unicode")

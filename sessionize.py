from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID
from xml.etree import ElementTree

from pydantic import BaseModel

from util import pentabarf_format_duration, xcal_format_duration


class Session(BaseModel):
    id: int
    title: str
    description: str
    startsAt: datetime
    endsAt: datetime
    roomId: int
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
    LinkedIn = "LinkedIn"
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


def event_to_pentabarf(event: Event) -> str:
    rooms = {room.id: room for room in event.rooms}
    speakers = {speaker.id: speaker for speaker in event.speakers}
    days = {session.startsAt.date() for session in event.sessions}

    root = ElementTree.Element("schedule")
    ElementTree.SubElement(root, "conference")

    for i, d in enumerate(sorted(days)):
        day = ElementTree.SubElement(
            root, "day", attrib={"index": str(i + 1), "date": d.strftime("%Y-%m-%d")}
        )

        for _, r in rooms.items():
            room = ElementTree.SubElement(day, "room", attrib={"name": r.name})

            for session in event.sessions:
                if session.startsAt.date() != d:
                    continue
                if session.roomId != r.id:
                    continue

                e = ElementTree.SubElement(
                    room, "event", attrib={"id": str(session.id)}
                )
                ElementTree.SubElement(e, "start").text = session.startsAt.strftime(
                    "%H:%M"
                )
                ElementTree.SubElement(e, "duration").text = pentabarf_format_duration(
                    session.startsAt, session.endsAt
                )
                ElementTree.SubElement(e, "room").text = r.name
                ElementTree.SubElement(e, "title").text = session.title
                ElementTree.SubElement(e, "description").text = session.description
                persons = ElementTree.SubElement(e, "persons")
                for s in session.speakers:
                    speaker = speakers[s]
                    ElementTree.SubElement(
                        persons, "person", attrib={"id": str(speaker.id)}
                    ).text = speaker.fullName

    ElementTree.indent(root, space="\t", level=0)
    return ElementTree.tostring(root, encoding="unicode")


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

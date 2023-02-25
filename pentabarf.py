from datetime import date, datetime, timedelta
from typing import List, Optional
from xml.etree import ElementTree

from pydantic import BaseModel


class Event(BaseModel):
    id: str
    start: datetime
    duration: timedelta
    room: str
    title: str
    track: Optional[str]
    description: str
    language: str
    persons: List[str]


class Room(BaseModel):
    name: str
    events: List[Event]


class Day(BaseModel):
    date: date
    rooms: List[Room]


class Conference(BaseModel):
    title: str
    city: str
    venue: str

    start: date
    end: date


class Schedule(BaseModel):
    conference: Conference
    days: List[Day]

    def to_xml(self) -> str:
        root = ElementTree.Element("schedule")
        conference = ElementTree.SubElement(root, "conference")
        ElementTree.SubElement(conference, "title").text = self.conference.title
        ElementTree.SubElement(conference, "city").text = self.conference.city

        if self.conference.venue:
            ElementTree.SubElement(conference, "venue").text = self.conference.venue

        ElementTree.SubElement(
            conference, "start"
        ).text = self.conference.start.strftime("%Y-%m-%d")
        ElementTree.SubElement(conference, "end").text = self.conference.end.strftime(
            "%Y-%m-%d"
        )

        for i, d in enumerate(sorted(self.days, key=lambda d: d.date)):
            day = ElementTree.SubElement(
                root,
                "day",
                attrib={"index": str(i + 1), "date": d.date.strftime("%Y-%m-%d")},
            )

            for r in sorted(d.rooms, key=lambda r: r.name):
                room = ElementTree.SubElement(day, "room", attrib={"name": r.name})

                for event in r.events:
                    e = ElementTree.SubElement(
                        room, "event", attrib={"id": str(event.id)}
                    )
                    ElementTree.SubElement(e, "start").text = event.start.strftime(
                        "%H:%M"
                    )
                    ElementTree.SubElement(e, "duration").text = self._format_duration(
                        event.duration
                    )
                    ElementTree.SubElement(e, "room").text = r.name
                    ElementTree.SubElement(e, "title").text = event.title
                    ElementTree.SubElement(e, "description").text = event.description
                    if event.track:
                        ElementTree.SubElement(e, "track").text = event.track
                    ElementTree.SubElement(e, "language").text = event.language

                    persons = ElementTree.SubElement(e, "persons")
                    for person in event.persons:
                        ElementTree.SubElement(persons, "person").text = person

        ElementTree.indent(root, space="\t", level=0)
        return ElementTree.tostring(root, encoding="unicode")

    @staticmethod
    def _format_duration(duration: timedelta) -> str:
        seconds = int(duration.total_seconds())

        hours = seconds // (60 * 60)
        seconds = seconds % (60 * 60)

        minutes = seconds // 60
        seconds = seconds % 60

        return f"{hours:02}:{minutes:02}"

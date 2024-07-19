from datetime import date, datetime
from typing import Any, Dict, List, Optional, Union

import requests
from devtools import debug
from pydantic import BaseModel

import pentabarf


class Talk(BaseModel):
    code: Optional[str]
    id: str
    title: Union[str, Dict[str, str]]
    abstract: Optional[str]
    start: datetime
    end: datetime
    room: int  # Room.id
    speakers: Optional[List[str]]  # List[Speaker.code]
    track: Optional[Any]
    duration: Optional[int]  # minutes
    updated: Optional[datetime]
    state: Optional[Any]


class Room(BaseModel):
    id: int
    name: Dict[str, str]
    description: Dict[Any, Any]


class Speaker(BaseModel):
    code: str
    name: str
    avatar: str  # URL


class Schedule(BaseModel):
    version: str
    talks: List[Talk]
    timezone: str
    event_start: date
    event_end: date
    tracks: List[Any]
    rooms: List[Room]
    speakers: List[Speaker]


def get_schedule(event: str, version: str) -> Schedule:
    response = requests.get(
        f"https://pretalx.com/{event}/schedule/v/{version}/widgets/schedule.json"
    )
    return Schedule(**response.json())


def schedule_to_pentabarf(
    schedule: Schedule, title: str, city: str, venue: str
) -> pentabarf.Schedule:
    speakers = {s.code: s.name for s in schedule.speakers}
    rooms_by_id = {r.id: r.name["en"] for r in schedule.rooms}
    rooms: Dict[int, pentabarf.Room] = {}
    for talk in schedule.talks:
        event = pentabarf.Event(
            id=talk.id,
            start=talk.start,
            duration=talk.end - talk.start,
            room=rooms_by_id.get(talk.room, ""),
            title=talk.title if isinstance(talk.title, str) else talk.title["en"],
            track=None,  # TODO
            description=talk.abstract or "",
            language="",  # TODO
            persons=[speakers.get(s) for s in talk.speakers or []],
        )

        if talk.room in rooms:
            rooms[talk.room].events.append(event)
        else:
            rooms[talk.room] = pentabarf.Room(
                name=event.room,
                events=[event],
            )

    return pentabarf.Schedule(
        conference=pentabarf.Conference(
            title=title,
            city=city,
            venue=venue,
            start=schedule.event_start,
            end=schedule.event_end,
        ),
        days=[pentabarf.Day(date=schedule.event_start, rooms=list(rooms.values()))],
    )

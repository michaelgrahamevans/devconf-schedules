#!/usr/bin/env python3

import json
import sys
from copy import deepcopy
from datetime import date, datetime, time
from enum import Enum
from typing import List, Optional
from uuid import UUID

import requests
from devtools import debug
from pydantic import BaseModel

from devconf import event_to_pentabarf, get_events
from sessionize import Event, Room, Session


def main():
    event_id = "p87oviq3"
    response = requests.get(f"https://sessionize.com/api/v2/{event_id}/view/all")
    event = Event(**response.json())

    events = get_events(event)
    for event in events:
        out = event_to_pentabarf(event)
        location = event.location.lower().replace(" ", "-")
        with open(f"schedules/devconf-{location}-2022.pentabarf.xml", "w") as f:
            f.write(out)


if __name__ == "__main__":
    main()

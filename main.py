#!/usr/bin/env python3
from datetime import date

import requests

import devconf
from devconf import event_to_pentabarf, get_event
from sessionize import Event


def main():
    config = devconf.Config(
        sessionize_id="p87oviq3",
        use_archive=True,
        locations=[
            devconf.Location(
                name="Cape Town", short_name="capetown", day=date(2022, 4, 5)
            ),
            devconf.Location(
                name="Virtual", short_name="virtual", day=date(2022, 4, 7)
            ),
            devconf.Location(
                name="Johannesburg", short_name="joburg", day=date(2022, 4, 7)
            ),
        ],
    )

    for location in config.locations:
        archive_datetime = location.day.strftime("%Y%m%d000000")
        response = requests.get(
            f"https://web.archive.org/web/{archive_datetime}/https://sessionize.com/api/v2/{config.sessionize_id}/view/all"
        )
        sessionize_event = Event(**response.json())

        event = get_event(sessionize_event, location, config.use_archive)
        out = event_to_pentabarf(event)

        loc = location.name.lower().replace(" ", "-")
        with open(
            f"schedules/devconf-{loc}-{location.day.year}.pentabarf.xml",
            "w",
        ) as f:
            f.write(out)


if __name__ == "__main__":
    main()

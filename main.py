#!/usr/bin/env python3
from datetime import date

import requests

import devconf
import sessionize


def main():
    config = devconf.Config(
        sessionize_id="p87oviq3",
        use_archive=True,
        events=[
            devconf.EventConfig(
                name="Cape Town", short_name="capetown", day=date(2022, 4, 5)
            ),
            devconf.EventConfig(
                name="Virtual", short_name="virtual", day=date(2022, 4, 7)
            ),
            devconf.EventConfig(
                name="Johannesburg", short_name="joburg", day=date(2022, 4, 7)
            ),
        ],
    )

    for event_config in config.events:
        archive_datetime = event_config.day.strftime("%Y%m%d000000")
        response = requests.get(
            f"https://web.archive.org/web/{archive_datetime}/https://sessionize.com/api/v2/{config.sessionize_id}/view/all"
        )
        sessionize_event = sessionize.Event(**response.json())

        event = devconf.get_event(sessionize_event, event_config, config.use_archive)
        out = devconf.event_to_pentabarf(event)

        loc = event_config.name.lower().replace(" ", "-")
        with open(
            f"schedules/devconf-{loc}-{event_config.day.year}.pentabarf.xml",
            "w",
        ) as f:
            f.write(out.to_xml())


if __name__ == "__main__":
    main()

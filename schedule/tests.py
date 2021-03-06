"""Nose tests for the Schedule submodule.

---

Copyright (c) 2013, University Radio York.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

* Redistributions of source code must retain the above copyright notice,
  this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright
  notice, this list of conditions and the following disclaimer in the
  documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import datetime
import functools
import operator
import unittest.mock

import lass.common.time
import lass.schedule.blocks
import lass.schedule.models


TEST_BLOCK_CONFIG = {
    'blocks': {
        'Test1': {
            'type': 'test_a'
        },
        'Test2': {
            'type': 'test_a'
        },
        'Test3': {
            'type': 'test_b'
        }
    },
    'range_blocks': [
        # Hour, minute, block
        [0, 0, 'Test1'],
        [7, 0, None],
        [9, 0, 'Test2'],
        [11, 0, None],
        [12, 0, 'Test3'],
        [14, 0, None],
        [19, 0, 'Test2'],
        [21, 0, 'Test1'],
    ],
    'name_blocks': [
        ['explicit name', 'Test1'],
        ['start*', 'Test2'],
        ['*finish', 'Test3'],
        ['exclude middle test', None],
        ['*middle*', 'Test1'],
        ['range[0123456789]', 'Test2']
    ]
}


#
# lass.schedule.blocks
#


def test_name_block_for_timeslot():
    """Tests 'lass.schedule.block.name_block_for_timeslot'."""
    timeslot = unittest.mock.MagicMock()

    block = lambda timeslot: (
        lass.schedule.blocks.name_block_for_timeslot(
            timeslot,
            TEST_BLOCK_CONFIG
        )
    )
    set_title = lambda timeslot, title: operator.setitem(
        timeslot.text['title'],
        0,
        title
    )
    timeslot.text = {'title': ['blank']}

    set_title(timeslot, 'explicit name')
    assert block(timeslot) == 'Test1', 'Explicit name matching failed.'

    set_title(timeslot, 'EXPLICIT NAME')
    assert block(timeslot) == 'Test1', 'Case is incorrectly sensitive.'

    set_title(timeslot, 'start test')
    assert block(timeslot) == 'Test2', 'Start-of-name matching failed.'

    set_title(timeslot, 'test finish')
    assert block(timeslot) == 'Test3', 'Finish-of-name matching failed.'

    set_title(timeslot, 'include middle test')
    assert block(timeslot) == 'Test1', 'Middle-of-name matching failed.'

    set_title(timeslot, 'exclude middle test')
    assert block(timeslot) is None, 'Exclusion rule ignored.'

    for i in range(0, 10):
        set_title(timeslot, 'range{}'.format(i))
        assert block(timeslot) == 'Test2', 'Character class matching failed.'

    set_title(timeslot, 'not a matched title')
    assert block(timeslot) is None, 'Fall-through failed.'

    set_title(timeslot, '')
    assert block(timeslot) is None, 'Empty string incorrectly matched.'


def test_name_block_match():
    """Tests 'lass.schedule.block.name_block_match'."""
    timeslot = unittest.mock.MagicMock()
    timeslot.text = {'title': ['The Quick Brown Fox Show']}

    match = functools.partial(
        lass.schedule.blocks.name_block_match,
        timeslot
    )

    # Should match against itself, obviously.
    assert match('The Quick Brown Fox Show')

    # Case insensitivity should apply.
    assert match('THE QUICK BROWN FOX SHOW')
    assert match('the quick brown fox show')

    # Should not match substrings or as a substring without *.
    assert not match('Quick Brown Fox')
    assert not match('Introducing The Quick Brown Fox Show')

    # Should match against a substring with *.
    assert match('The Quick Brown*')
    assert match('*Quick Brown Fox*')
    assert match('*Brown Fox Show')

    # Should match character classes too, explicitly at least.
    assert match('The Quick Brown F[ao]x Show')

    # Should match wildcard...
    assert match('*')

    # And not match empty.
    assert not match('')


def test_range_iter():
    """Tests 'lass.schedule.block.range_iter'."""
    blocks = TEST_BLOCK_CONFIG['range_blocks']
    time_context = lass.common.time.TimeContext('Europe/London', [], 7)
    start_date = time_context.start_on(
        time_context.schedule_date_of(lass.common.time.aware_now())
    )

    r = lass.schedule.blocks.range_iter(
        blocks,
        start_date,
        time_context
    )

    # Should yield (datetime, name) for each (hour, minute, name).
    # Go around the list twice to make sure the iterator repeats itself.
    for hour, minute, name in (blocks + blocks):
        iter_datetime, iter_name = next(r)

        assert iter_name == name
        assert iter_datetime.hour == hour
        assert iter_datetime.minute == minute


#
# lass.schedule.models
#


def test_show_schedule_seasons():
    """Tests 'lass.schedule.models.Show.scheduled_seasons'."""
    show = lass.schedule.models.Show(submitted_at=lass.common.time.aware_now())

    # If no seasons, there should be no scheduled seasons.

    show.seasons = []
    assert show.scheduled_seasons == []

    # scheduled_seasons should contain only seasons whose timeslots
    # attribute is not empty.

    timeslot = lass.schedule.models.Timeslot(
        start=lass.common.time.aware_now(),
        duration=datetime.timedelta(hours=1)
    )

    bad_season = lass.schedule.models.Season(show=show)
    bad_season.timeslots = []

    good_season = lass.schedule.models.Season(show=show)
    good_season.timeslots = [timeslot]

    show.seasons = [bad_season]
    assert show.scheduled_seasons == []

    show.seasons = [good_season]
    assert show.scheduled_seasons == [good_season]

    show.seasons = [bad_season, good_season]
    assert show.scheduled_seasons == [good_season]

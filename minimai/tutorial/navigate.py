from sonolus.script.runtime import navigation_direction

from minimai.tutorial.update import next_section, previous_section


def navigate():
    if navigation_direction() > 0:
        next_section()
    else:
        previous_section()

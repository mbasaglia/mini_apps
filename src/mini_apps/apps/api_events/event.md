**{{ event.title }}**[{{ invis }}]({event.image})
{% if event.description -%}
{{ event.description }}
{%- endif %}

**Held on** {{ event.start.strftime("%A %d") }}
**Starts at** {{ event.start.strftime("%H:%M") }}
**Ends at** {{ event.finish.strftime("%H:%M") }}
**Duration** {{ minutes(event.duration) }}
**Location** {{ event.location }}

[View Events](https://t.me/{{ me.username }}/{{ shortname }}?startapp={{ event.id }})

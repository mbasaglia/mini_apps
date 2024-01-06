**{{ event.title }}**[\u200B]({event.image})
{% if event.description -%}
{{ event.description }}
{%- endif %}

**Starts** {{ event.start.strftime("%A %d %H:%M") }}
**Duration** {{ minutes(event.duration) }}
**Location** {{ event.location }}

[View Events](https://t.me/{me.username}/{shortname}?startapp={event.id})

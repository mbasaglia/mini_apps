**{{ event.title }}**[{{ invis }}]({{ event.image }})
{% if event.description -%}
{{ event.description }}
{%- endif %}

**Held on** {{ event.start.strftime("%A %d") }}
**Starts at** {{ event.start.strftime("%H:%M") }} {% if event.start < now < event.finish -%}
    (Already started)
{%- endif %}
**Ends at** {{ event.finish.strftime("%H:%M") }}
**Duration** {{ minutes(event.duration) }}
**Location** {{ event.location }}

[View Events]({{ mini_app_link }}?startapp={{ event.id }})

**{{ event.title }}**
{% if event.description -%}
{{ html_to_markdown(event.description) }}
{%- endif %}

**Held on** {{ event.start.strftime("%A %d") }}
**Starts at** {% if event.duration >= 60 * 24 -%}
    {{ event.start.strftime("%H:%M %a %d") }}
{%- else -%}
    {{ event.start.strftime("%H:%M") }}
{%- endif %} {% if event.start < now < event.finish -%}
    (Already started)
{%- endif %}
**Ends at** {% if event.duration >= 60 * 24 -%}
    {{ event.finish.strftime("%H:%M %a %d") }}
{%- else -%}
    {{ event.finish.strftime("%H:%M") }}
{%- endif %}
**Duration** {{ minutes(event.duration) }}
**Location** {{ event.location }}

[View Events]({{ mini_app_link }}?startapp={{ event.id }})

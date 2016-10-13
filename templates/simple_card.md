{% if card.summary %}
**{{card.summary}}**
{% endif %}
{% if not card.thumbnail %}
{% if card.link %}
##[{{ card.title }}]({{ card.link }})
{% else %}
##{{ card.title }}
{% endif %}
{% else %}
{% if card.link %}

| |
|-:|:-
| ![{{ card.thumbnail }}]({{ card.thumbnail }}) | **[{{ card.title }}]({{ card.link }})**

{% else %}

| |
|-:|:-
| ![{{ card.thumbnail }}]({{ card.thumbnail }}) | **{{ card.title }}**

{% endif %}
{% endif %}

{% for key, value in card.fields %}{{ key }}: {{value}} {% endfor %}


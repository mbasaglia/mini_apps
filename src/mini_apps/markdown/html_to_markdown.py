import xml.etree.ElementTree as etree


def wrap_element(element, mark, list_depth=0):
    content = content_to_markdown(element, list_depth)
    return mark + content + mark + (element.tail or "")


def blocks_to_markdown(element: etree.Element):
    return "\n".join(map(element_to_markdown, element))


def content_to_markdown(element: etree.Element, list_depth):
    content = element.text or ""
    for child in element:
        content += element_to_markdown(child, list_depth)
    return content


def element_to_markdown(element: etree.Element, list_depth=0):
    if element.tag.startswith("h") and element.tag[-1].isdigit():
        return wrap_element(element, "**")
    elif element.tag in ["em", "i"]:
        return wrap_element(element, "__")
    elif element.tag in ["strong", "b"]:
        return wrap_element(element, "**")
    elif element.tag in ["s"]:
        return wrap_element(element, "~~")
    elif element.tag in ["code"]:
        return wrap_element(element, "`")
    elif element.tag in ["pre"]:
        if len(element) == 1 and element[0].tag == "code":
            inner = element[0]
        else:
            inner = element
        return "```\n%s\n```" % content_to_markdown(inner)
    elif element.tag == "a":
        text = element.text or ""
        url = element.attrib["href"]
        if text == url:
            return url
        return "[%s](%s)%s" % (text, url, element.tail or "")
    elif element.tag in ["span"]:
        return wrap_element(element, "")
    elif element.tag in ["ul", "ol"]:
        text = ""
        for child in element:
            text += "%s* %s\n" % (list_depth * 4 * " ", element_to_markdown(child, list_depth + 1))
        return text
    else:
        return content_to_markdown(element, list_depth).strip("\n") + "\n"


def html_to_markdown(html):
    """
    Converts an HTML string to telegram markdown
    """
    top = etree.fromstring("<html>%s</html>" % html)
    return blocks_to_markdown(top)

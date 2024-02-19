import re
import markdown
import xml.etree.ElementTree as etree


class AutoLinkPattern(markdown.inlinepatterns.InlineProcessor):
    re_url = r"https?://[-a-zA-Z0-9@:%._\+~#=]+\.[a-zA-Z0-9()]+\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
    re_trim_tail = re.compile(r"[).,;:!?]+$")

    def __init__(self, md):
        super().__init__(self.re_url, md)

    def handleMatch(self, match, data):
        url = match.group(0)

        trim = self.re_trim_tail.search(url)
        end = match.end(0)
        if trim:
            end = match.start(0) + trim.start(0)
            url = url[:trim.start(0)]

        text = url
        el = etree.Element("a")
        el.set('href', url)
        el.text = text
        return el, match.start(0), end


class AutoLinkExtension(markdown.Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(AutoLinkPattern(md), "autolink", 175)

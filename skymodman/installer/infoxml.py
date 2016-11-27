"""Parse the info.xml file present in FOMOD/other archives"""

from skymodman.thirdparty.untangle import untangle

example_xml="""
<?xml version="1.0" encoding="UTF-16"?>
<!--header line may not be present-->
<fomod>
  <Name>Super Duper Mod Redux</Name>
  <Author>Arthur McModder</Author>
  <Email>PM ArtyMcModdy at Skyrim Nexus</Email> <!--obv. not always an email-->
  <Version>1.4.2</Version>
  <LastKnownVersion>1.6a</LastKnownVersion> <!--What the heck is this? Only rarely seen-->
  <Id>12345678</Id> <!--(Optional?)-->
  <Description>
This Mod does really cool things.

I mean like crazy things.

Note: The things are cool.

Note2: This description may not be present. Or may be empty. And [b]may[/b] include bbcode.
  </Description>
  <Website>http://www.nexusmods.com/skyrim/mods/12345678</Website>
  <!--<Website type="old format">http://skyrim.nexusmods.com/mods/12345678/</Website>-->

  <Groups> <!--(Optional?)-->
    <element>Immersion</element>
    <element>replacers/textures</element>
  </Groups>
</fomod>
"""

class InfoXML:

    __slots__ = ("name", "author", "version", "id", "website",
                 "email", "description", "groups")

    def __init__(self, info_xml):
        xinfo = untangle.parse(info_xml)

        root = xinfo.fomod

        for el in ("name", "author", "version",
                   "id", "website", "email"):
            # pull the text from the xml and assign to appropriate
            # instance attribute; if an element is not present in the
            # xml file, the attribute will be set to ``None``
            self.get_set_value(root, el)

        # description: could be multi-line. todo: handle specially
        self.get_set_value(root, "description")

        # groups: could be multiple
        self.groups = []
        try:
            groups = root.Groups
            for g in groups.element:
                # avoid empty elements
                text = g.cdata.strip()
                if text:
                    self.groups.append(text)
        except AttributeError as e:
            # print("Groups AttributeError:", e)
            # no listed groups
            pass


    def get_set_value(self, root, name):
        try:
            element = _elgetter[name](root)
        except AttributeError:
            # xml did not include the requested element
            setattr(self, name, None)
        else:
            setattr(self, name, element.cdata.strip())

_elgetter = {
    "name": lambda r: r.Name,
    "author": lambda r: r.Author,
    "version": lambda r: r.Version,
    "id": lambda r: r.Id,
    "website": lambda r: r.Website,
    "description": lambda r: r.Description,
    "email": lambda r: r.Email,
}



if __name__ == '__main__':
    info = InfoXML('res/STEP/info.xml')

    for s in InfoXML.__slots__:
        print(s, getattr(info, s), sep=": ")

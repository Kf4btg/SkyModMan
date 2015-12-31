from . import IModInstaller
import easygui as eg
import textwrap


class EGInstaller(IModInstaller):
    tw = textwrap.TextWrapper(width=90, tabsize=2, replace_whitespace=False, initial_indent='  ', subsequent_indent='  ')

    def __init__(self, modname):
        IModInstaller.__init__(self, modname)


    def selectAny(self, plugin_list):
        choices = []

        for plugin in plugin_list:
            if not self.shouldShowPlugin(plugin):
                continue
            choices.append((plugin.name, self.wrap(plugin.description)))

        if choices:
            msg = self.group.name
            results  = eg.multchoicebox(msg, self.step.name, choices)

            return results

    def wrap(self, string:str):
        lines = string.splitlines()
        wrapped_lines = []
        for line in lines:
            wrapped_lines.append(self.tw.fill(line))

        return "\n".join(wrapped_lines)
import sh
from . import IModInstaller, InstallerBase
import textwrap



_std_args   = ["--ok-label=Next"]

_yesno_args = ["--question",
               "--ok-label=Yes",
               "--cancel-label=No"]

_list_args  = ["--list",
               "--hide-header",
               "--separator=\n"] # \n necessary for returning a list rather than a string

_list_column_args = ["--column=Name",
                     "--column=Description",
                     "--column=Index"] # index used to reference which item(s) were selected in the list

_checklist_args = ["--checklist",
                   "--multiple"]
_radiolist_args = ["--radiolist"]

def _call_zen(*args, **kwargs):
    """
    A wrapper around the sh.zenity() command call that (should) gracefully
    handle the user clicking the "Cancel" button at any time during
    the installation process by presenting a Confirm-Quit dialog;
    if they decide to quit, the default quitInstaller() method will
    call sys.exit(0) to cleanly exit; if they decide to go back to the
    installer, the previously-displayed dialog will be shown again and
    they can continue where they left off.
    :param args:
    :param kwargs:
    :return:
    """
    try:
        return sh.zenity(*args, **kwargs)
    except sh.ErrorReturnCode_1:
        # user pressed cancel button...maybe
        try:
            sh.zenity("--question", "--window-icon=warning","--title=Exit Installer",
                  "--text=Are you sure you want to quit the installer? No changes have been made to your mod setup.",
                  "--ok-label=Go Back", "--cancel-label=Quit")
        except sh.ErrorReturnCode_1:
            ZenityInstaller.quitInstaller()
        _call_zen(*args, **kwargs) #redisplay the previous dialog if they decide not to quit

def _addResult(results: list, source_list: list, index ):
    """default stdout-handling callback for the sh.zenity calls.
    Appends the item at index :index: in :source_list: to the :results:"""
    if isinstance(index, str):
        index = int(index)

    results.append(source_list[index])


def _showZenityDialog(dlgtype:str, title:str, text:str,
                      result_container: list = None,
                      sources:list=None, choices: list=None,
                      width:int=0, height:int=0, *extra_args,
                      verifier = None, **kwargs):
    """

    :param dlgtype: e.g. "list", "checklist", "radiolist", "question"
    :param title: title of the zenity window
    :param text: text to display
    :param result_container: a list object that will be used to hold the
    results of the zenity command; if this information is not needed, leave
    this parameter as None
    :param sources: The original sources list (e.g. list of plugins) from which
    the choices were pulled; required if a list-type dialog is used
    :param choices: The filtered (by dependency type) sequence of plugins to show as
     as choices, formatted properly for the zenity dialogs; required if a
     list-type dialog is used.
    :param width: specify a number greater than 0 to give the window a fixed width
    :param height: specify a number greater than 0 to give the window a fixed height
    :param extra_args: sequence of any extra parameters to pass to zenity, formatted
    as cli-arguments (e.g. ["--timeout=600", "--window-icon=path/to/icon"])
    :param verifier: a function that takes the results list as a parameter and returns
     a boolean value indicating whether or not the results are valid. If a
     False value is received from the verification callback, the dialog will
     be shown again.
    :param kwargs: use keyword-args to pass special-variable arguments to sh
    :return:
    """

    args=["--title="+title, "--text="+text]
    if width  > 0: args+=["--width={}".format(width)]
    if height > 0: args+=["--height={}".format(height)]

    if dlgtype.endswith("list"):
        assert sources is not None
        assert choices is not None
        # common list arguments
        args+=[*_std_args, *_list_args]

        if dlgtype == "checklist":
            args+=_checklist_args
            col_args = ["--column=Selected", *_list_column_args]
        elif dlgtype == "radiolist":
            args+=[*_radiolist_args]
            col_args = ["--column=Selected", *_list_column_args]
        else:
            # plain list has no "selected" column
            col_args = _list_column_args

        args+=["--hide-column={}".format(len(col_args)),
               "--print-column={}".format(len(col_args)),
               *col_args, *choices]

    elif dlgtype == "question": #yesno
        args+=[*_yesno_args]
        # don't need to deal with all the verification
        # junk for yes/no dialogs. Calling function should
        # handle the exception thrown if the no button is pressed
        return sh.zenity(*args, *extra_args, **kwargs)

    else:
        args+=_std_args

    args+=extra_args

    if result_container is None:
        result_container = []

    _call_zen(*args, **kwargs, _out=lambda r: _addResult(result_container, sources, r))
    if verifier is not None:
        while not verifier(result_container):
            result_container.clear()
            # redisplay the dialog
            _call_zen(*args, **kwargs, _out=lambda r: _addResult(result_container, sources, r))



zen = _showZenityDialog


def SEOverifier(result_list: list) -> bool:
    """verification callback for the "select-exactly-one" plugins"""
    if len(result_list) != 1:
        output = _call_zen("--warning", "--text=Exactly one option must be chosen.")
        # print(output.exit_code)
        return False
    return True


class ZenityInstaller(InstallerBase):
    """
    uses python-sh to create and call zenity dialogs for the installation steps
    """

    # for pretty-formatting of the option descriptions;
    # indents used for padding
    tw = textwrap.TextWrapper(width=90, tabsize=2, replace_whitespace=False, initial_indent='  ', subsequent_indent='  ')
    # for keeping the option-name fields a reasonable width
    ntw = textwrap.TextWrapper(width=30, tabsize=2, initial_indent=' ', subsequent_indent=' ')



    def __init__(self, mod, width=1024, height=600):
        IModInstaller.__init__(self, mod)
        self.width  = width
        self.height = height

    @property
    def h(self) -> int:
        return self.height
    @property
    def w(self) -> int:
        return self.width

    def selectAny(self, plugin_list):
        choices = []

        index=-1
        for plugin in plugin_list:
            index+=1
            if not self.shouldShowPlugin(plugin):
                continue
            choices.append(["TRUE", self.ntw.fill(plugin.name), self.wrap(plugin.description), index])

        if choices:
            results = []
            text = self.group.name
            text+=" (Select Any)"
            zen("checklist", self.step.name, text,
                results, plugin_list, choices, self.w, self.h)
            # _out = lambda r: _addResult(results, plugin_list, r))

            return results

    def yesNo(self, plugin_list):
        y = plugin_list[0 if plugin_list[0].name == "Yes" else 1]
        n = plugin_list[1 if plugin_list[0].name == "Yes" else 0]

        oii = self.tw.initial_indent
        osi = self.tw.subsequent_indent

        self.tw.initial_indent = self.tw.subsequent_indent='        '
        text = '<span size="larger" weight="bold">{question}</span>\n\n'.format(question=self.group.name) + \
               '<b>Yes</b>:\n{ydesc}\n\n<b>No</b>:\n{ndesc}'.format(ydesc=self.wrap(y.description),
                                                                    ndesc=self.wrap(n.description))

        self.tw.initial_indent = oii
        self.tw.subsequent_indent = osi

        try:
            zen("question", self.step.name, text) #, width=self.w, height=self.h)
            return [y]

        except sh.ErrorReturnCode_1:
            # "No" button clicked
            return [n]

    def selectExactlyOne(self, plugin_list):
        if self.isYesNo(plugin_list):
            return self.yesNo(plugin_list)
        choices = []

        # used for referencing
        index = -1
        for plugin in plugin_list:
            index+=1
            if not self.shouldShowPlugin(plugin):
                continue

            choices.append(["TRUE" if len(choices)==0 else "FALSE", self.ntw.fill(plugin.name), self.wrap(plugin.description),
                            index])

        if choices:
            result=[]
            text = self.group.name
            text+=" (Select One)" #debug
            zen("radiolist", self.step.name, text,
                result, plugin_list, choices,
                self.w, self.h,
                verifier=SEOverifier)

            return result

    def selectAtMostOne(self, plugin_list):
        choices = []

        index = -1
        for plugin in plugin_list:
            index+=1
            if not self.shouldShowPlugin(plugin):
                continue
            choices.append([self.ntw.fill(plugin.name), self.wrap(plugin.description), index])
        if choices:
            result=[]
            text = self.group.name
            text+=" (Select At Most One)"
            zen("list", self.step.name, text,
                result, plugin_list, choices,
                width=self.w, height=self.h)
                # _out=lambda r: _addResult(result, plugin_list, r))
            return result

    def wrap(self, string:str):
        lines = string.splitlines()
        wrapped_lines = []
        for line in lines:
            wrapped_lines.append(self.tw.fill(line))

        return "\n".join(wrapped_lines)

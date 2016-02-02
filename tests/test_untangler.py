from skymodman.fomod.untangler import Fomodder
import pytest

@pytest.fixture(scope='module')
def config(xmlfile='res/STEP/ModuleConfig.xml'):
    return Fomodder(xmlfile)


@pytest.fixture(scope='module')
def stepper():
    return config().get_stepper()


def test_root(config):
    assert config.root._name == "config"


def test_modname(stepper):
    assert stepper.count == 0

    # first, the element name is announced
    assert stepper.step == "moduleName"
    assert stepper.count == 1

    # followed by cdata, if any
    assert stepper.step == "The STEP Installer"

    # then the attributes
    nstep = stepper.step
    # coming from dict, could be in any order
    assert nstep in ["position", "colour"]
    if nstep == "position":
        assert stepper.step == "RightOfImage"
        assert stepper.step == "colour"
        assert str(stepper.step) == "000000"

    elif nstep == "colour":
        assert str(stepper.step) == "000000"
        assert stepper.step == "position"
        assert stepper.step == "RightOfImage"


def test_modimage(stepper):
    assert stepper.step == "moduleImage"

    attrs = [("path", "screenshot"),
             ("showImage", True),
             ("showFade", True),
             ("height", -1)]

    for j in range(4):
        a_next = stepper.step
        for i in range(len(attrs)):
            if attrs[i][0]==a_next:
                assert attrs[i][1]==stepper.step
                attrs.pop(i)
                break

    assert len(attrs) == 0

    # and next is when we'd test the module dependencies,
    # but the STEP installed doesn't have them, so...

def test_required_install_files(stepper):
    assert stepper.step == "requiredInstallFiles"
    nstep = stepper.step

    assert nstep in ["file", "folder"]

    expects={
        "file": [{
            "source": "00 Core Files",
            "destination": "",
            "priority": 2,
            "alwaysInstall":   False,
            "installIfUsable": False,
            },{
            "source":      "01 Core Files",
            "destination": "",
            "priority":    1,
            "alwaysInstall":   False,
            "installIfUsable": False,
        }],
        "folder": [{
            "source":      "00 Core Files",
            "destination": "",
            "priority":    1,
            "alwaysInstall":   False,
            "installIfUsable": False,
        }]
    }

    check_file_item(stepper, nstep, expects)
    check_file_item(stepper, stepper.step, expects)
    check_file_item(stepper, stepper.step, expects)

    assert expects == {"file":[], "folder":[]}





## test helpers
def check_file_item(_stepper, file_type, possibles):
    # attributes are source, destination, priority,alwaysInstall,installIfUsable
    # in a random order

    attr={_stepper.step: _stepper.step,
          _stepper.step: _stepper.step,
          _stepper.step: _stepper.step,
          _stepper.step: _stepper.step,
          _stepper.step: _stepper.step}

    assert attr in possibles[file_type]
    possibles[file_type].remove(attr)






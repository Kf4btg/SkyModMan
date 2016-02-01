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
        assert stepper.step == "000000"

    elif nstep == "colour":
        assert stepper.step == "000000"
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



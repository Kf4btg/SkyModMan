#!/usr/bin/env python3


#======================================
#   CONSTRUCTION FUNCTION JUNCTION
#======================================

from lxml import objectify
from pprint import pprint
from fomod import lxmlParse
# from fomod.elements import ModName, DependencyList, DependencyType, FileList, InstallSteps, ModImage, Pattern, DTPattern, Group, Plugin
# from fomod.enums import *




#===================================
#   TESTING
#===================================

def test():
    # fmod = Fomod('Fomod/ModuleConfig.xml')
    # print(etree.tostring(fmod.config, pretty_print=True, encoding='unicode'))
    # etree.dump(fmod.config, pretty_print=True)
    # pprint(fmod.config)

    # moduleName = fmod.config.findtext("moduleName")


    # x = etree.XPathEvaluator(fmod.config)
    #
    # folders = []
    # files = []
    # for f in x("//requiredInstallFiles/*"):
    #     if f.tag == "folder":
    #         folders.append(attrToDict(f))
    #     else:
    #         files.append(attrToDict(f))
    #
    # print(files,folders)
    # c = fmod.config
    # print(objectify.dump(c))
    # modName = c.moduleName


    ## e.g., what is the "screenshot" that is supposed
    ## to be used if the path attribute doesn't exist?
    # modImage = c.image.get("path") # or screenshot_path
    # modImage_show = c.image.get("showImage") or True
    # modImage_showFade = c.image.get("showFade") or True
    # modImage_height = int(c.image.get("height")) or -1

    # try:
    #     modDeps = DependencyList(c.moduleDependencies.dependencies.get("operator"))
    #     modDeps.parseXMLDepList(c.moduleDependencies.dependencies.iterchildren())
    # except AttributeError:
    #     modDeps = None

    # print (objectify.dump(c.requiredInstallFiles))
    # print ([ f.items() for f in c.requiredInstallFiles.getchildren()])
    # requiredFiles = { 'folder': [], 'file': [] }
    # for f in c.requiredInstallFiles.getchildren():
    #     requiredFiles[f.tag].append(dict(f.items()))

    # print(requiredFiles)

    # installStepOrder = c.installSteps.get("order") or "Ascending"

    # print(installStepOrder)


    # patAddDep = {
    #     "fileDependency": lambda p,d: p.addDependency(d.tag, file=d.get("file"), state=d.get("state")),
    #     "flagDependency": lambda p,d: p.addDependency(d.tag, flag=d.get("flag"), value=d.get("value")),
    #     "gameDependency": lambda p,d: p.addDependency(d.tag, version=d.get("version")),
    #     "fommDependency": lambda p,d: p.addDependency(d.tag, version=d.get("version"))
    # }

    # steps = InstallSteps(installStepOrder)
    # for step in c.installSteps.installStep:
        # print (objectify.dump(step))

        # step_name = step.get("name")
        # print(step_name)

        # optFileGroups = []
        # for g in step.optionalFileGroups.group:
        #     group = Group(name=g.get("name"),
        #             group_type=g.get("type"),
        #             plugin_order=g.plugins.get("order") or "Ascending")
        #     for p in g.plugins.plugin:
        #         try:
        #             type_desc = p.typeDescriptor.type.get("name")
        #         except AttributeError:
                    # means this is a complex dependency type
                    # dt = p.typeDescriptor.dependencyType
                    # type_name = dt.defaultType.get("name")

                    # type_desc = DependencyType(dt.defaultType.get("name"))

                    # for elPat in dt.patterns.pattern:
                    #     pat = DTPattern(elPat)
                        # for dep in elPat.dependencies.iterchildren():
                        #     patAddDep[dep.tag](pat, dep)
                        #
                        # try:
                        #     for f in elPat.files.iterchildren():
                        #         pat.addFile(f.tag, **dict(f.items()))
                        # except AttributeError:
                        #     pass

                        # type_desc.addPattern(pat)

                    # for P in patterns:
                    #     print(P.pluginType)
                    #     pprint(P.deps)
                        # patterns.append({ "dependencies" : { "operator" : pat.dependencies.get("operator"),  }  })

                # try:
                #     p_image = p.image.get("path")
                # except AttributeError:
                #     p_image = None
                # plug = Plugin(name=p.get("name"), description=p.description.text, type_descriptor=type_desc, image=p_image)

                # try:
                #     for flag in p.conditionFlags.flag:
                #         plug.addConditionFlag(flag.get("name"), flag.text)
                # except AttributeError:
                #     pass

                # try:
                #     for f in p.files.iterchildren():
                #         plug.addFile(f.tag, **dict(f.items()))
                # except AttributeError:
                #     pass

                # group.addPlugin(plug)

            # optFileGroups.append(group)

        # try:
        #     vis = Visible(step.visible.dependencies.get("operator"))
        #     for dep in step.visible.dependencies.iterchildren():
        #         patAddDep[dep.tag](vis, dep)
        # except AttributeError:
        #     vis=None

        # steps.addStep(step_name, optionalFileGroups = optFileGroups, visible = vis)

    # conditionalFileInstalls = []
    # for p in c.conditionalFileInstalls.patterns.pattern:
    #     pat = Pattern(p)
        # for dep in p.dependencies.iterchildren():
        #     patAddDep[dep.tag](pat, dep)

        # try:
        #     for f in p.files.iterchildren():
        #         pat.addFile(f.tag, **dict(f.items()))
        # except AttributeError:
        #     pass

        # conditionalFileInstalls.append(pat)

    # print("Mod Name: " + modName)
    #
    # print("Mod Dependencies: {}\n".format(modDeps))
    #
    # print("Required Install Files:")
    # pprint(requiredFiles)
    #
    # print("Install Steps:\n")
    #
    # for s in steps.steps:
    #     print("Step name: "+s["name"]+'\n')
    #     print("Visible:\n " + str(s["visible"]))
    #     print("OptionalFileGroups: ")
    #     [print(g) for g in s["optionalFileGroups"]]
    #     print ("--")
    #
    # print("Conditional File Installs")
    # print("-------------------------")
    # for i in range(len(conditionalFileInstalls)):
    #     print("#{}:: {}".format(i+1,conditionalFileInstalls[i]))


    # print(etree.tostring(c, pretty_print=True))
    objectify.enable_recursive_str(True)
    print(objectify.dump(objectify.parse('Fomod/ModuleConfig.xml').getroot()))
    objectify.enable_recursive_str(False)


def test2():
    fomod = lxmlParse('Fomod/ModuleConfig.xml')

    print("Mod Name: {}".format(fomod.module_name))
    print("Mod Image: {}".format(fomod.module_image))

    print("Mod Dependencies: {}\n".format(fomod.module_dependencies))

    print("Required Install Files:")
    pprint(fomod.required_install_files)

    print("Install Steps:\n")

    for s in fomod.install_steps.steps:
        print("Step name: "+s["name"]+'\n')
        print("Visible:\n " + str(s["visible"]))
        print("OptionalFileGroups: ")
        [print(g) for g in s["optionalFileGroups"]]
        print ("--")

    print("Conditional File Installs")
    print("-------------------------")
    for i in range(len(fomod.conditional_file_installs)):
        print("#{}:: {}".format(i+1,fomod.conditional_file_installs[i]))

def test3():
    fomod = lxmlParse('res/STEP/ModuleConfig.xml')
    # pprint(fomod.__dict__, depth=10)

    print("Mod Name\n"
          "-------------------------")
    print(fomod.module_name)
    print("Mod Image\n"
          "-------------------------")
    print(fomod.module_image)
    print("\nMod Dependencies\n"
          "-------------------------")
    print(fomod.module_dependencies)
    print("\nRequired Install Files\n"
          "-------------------------")
    print(fomod.required_install_files)
    print("Install Steps\n"
          "-------------------------")
    print(fomod.install_steps)

    print("Conditional File Installs\n"
          "-------------------------")
    pprint(fomod.conditional_file_installs)


def test4():
    import sys
    from PyQt5.QtWidgets import QApplication
    import fomod.installer.qt5 as qt

    app = QApplication(sys.argv)
    main = qt.QTInstaller("testing")

    main.show()
    sys.exit(app.exec_())

if __name__=='__main__':
    # test()
    # test2()
    # test3()
    test4()
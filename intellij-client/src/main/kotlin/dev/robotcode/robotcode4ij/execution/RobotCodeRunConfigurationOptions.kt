package dev.robotcode.robotcode4ij.execution

import com.intellij.execution.configurations.ModuleBasedConfigurationOptions
import com.intellij.openapi.components.BaseState
import com.intellij.util.xmlb.annotations.Tag
import com.intellij.util.xmlb.annotations.XCollection
import com.intellij.util.xmlb.annotations.XMap

/** What a Robot Framework run configuration runs. */
enum class RobotRunTargetKind {
    /**
     * The given files and folders, which replace the paths of `robot.toml`; without any, the paths of `robot.toml` or
     * the project folder run.
     */
    PATHS,

    /** Tests, tasks and suites that a gutter or context run selected, or that the user entered. */
    SELECTION
}

/** How a run sets Robot Framework's mode. */
enum class RobotRunMode {
    /**
     * The mode of the "Robot" settings page; while that is the default, nothing is passed, so `robot.toml` and the
     * suites decide.
     */
    INHERIT,

    /** `--rpa` */
    RPA,

    /** `--norpa` */
    NORPA
}

/** Which profiles of `robot.toml` a run selects. */
enum class RobotRunProfilesKind {
    /** The profiles selected for the project when the run starts. */
    PROJECT,

    /** No `-p`, so that the `default-profiles` of `robot.toml` apply. */
    DEFAULTS,

    /** The configuration's own profiles; without any, the `default-profiles` of `robot.toml` apply. */
    CUSTOM
}

/**
 * One item of a "Tests and suites" target, with the full names and paths that discovery reports. An item that the user
 * entered in the editor has only a full name.
 */
@Tag("item")
class RobotRunSelectionItem : BaseState() {
    // test, task or suite
    var kind by string()
    var name by string()

    // the item's own name, for the name of a configuration created from context
    var label by string()
    var relSource by string()

    // the suite that `-s` and `-I` select for the item
    var suite by string()
    var suiteRelSource by string()
}

/**
 * The RobotCode values of a run configuration, stored next to PyCharm's own fields of the configuration.
 */
class RobotCodeRunConfigurationOptions : ModuleBasedConfigurationOptions() {
    var targetKind by enum(RobotRunTargetKind.PATHS)

    @get:XCollection(propertyElementName = "targetPaths", elementName = "path", valueAttributeName = "value")
    var targetPaths by list<String>()

    @get:XCollection(propertyElementName = "selection")
    var selection by list<RobotRunSelectionItem>()

    // the name of the top-level suite that discovery reported when the items were selected
    var topLevelSuite by string()

    // the Robot Framework options of the configuration; unset values pass nothing
    var robotArguments by string()

    @get:XMap(
        propertyElementName = "variables", entryTagName = "variable", keyAttributeName = "name",
        valueAttributeName = "value"
    )
    var variables: MutableMap<String, String> by linkedMap()

    @get:XCollection(propertyElementName = "variableFiles", elementName = "file", valueAttributeName = "value")
    var variableFiles by list<String>()

    @get:XCollection(propertyElementName = "pythonPath", elementName = "path", valueAttributeName = "value")
    var pythonPath by list<String>()

    @get:XCollection(propertyElementName = "languages", elementName = "language", valueAttributeName = "value")
    var languages by list<String>()

    @get:XCollection(propertyElementName = "includeTags", elementName = "tag", valueAttributeName = "value")
    var includeTags by list<String>()

    @get:XCollection(propertyElementName = "excludeTags", elementName = "tag", valueAttributeName = "value")
    var excludeTags by list<String>()

    var outputDir by string()

    var mode by enum(RobotRunMode.INHERIT)

    var dryRun by property(false)

    // the profiles of robot.toml that runs select; the names are those of CUSTOM
    var profilesKind by enum(RobotRunProfilesKind.PROJECT)

    @get:XCollection(propertyElementName = "profiles", elementName = "profile", valueAttributeName = "value")
    var profiles by list<String>()
}

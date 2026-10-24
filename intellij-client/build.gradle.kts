import org.jetbrains.changelog.markdownToHTML
import org.jetbrains.intellij.platform.gradle.Constants.Constraints
import org.jetbrains.intellij.platform.gradle.IntelliJPlatformType
import org.jetbrains.intellij.platform.gradle.TestFrameworkType
import org.jetbrains.intellij.platform.gradle.extensions.IntelliJPlatformTestingExtension
import org.jetbrains.intellij.platform.gradle.models.ProductRelease
import org.jetbrains.intellij.platform.gradle.providers.ProductReleasesFilterParameters
import org.jetbrains.intellij.platform.gradle.tasks.PrepareSandboxTask
import org.jetbrains.intellij.platform.gradle.tasks.VerifyPluginTask.FailureLevel.COMPATIBILITY_PROBLEMS
import org.jetbrains.intellij.platform.gradle.tasks.VerifyPluginTask.FailureLevel.INVALID_PLUGIN
import org.jetbrains.intellij.platform.gradle.tasks.VerifyPluginTask.FailureLevel.MISSING_DEPENDENCIES
import org.jetbrains.intellij.platform.gradle.tasks.VerifyPluginTask.VerificationReportsFormats.MARKDOWN
import org.jetbrains.intellij.platform.gradle.tasks.VerifyPluginTask.VerificationReportsFormats.PLAIN
import org.jetbrains.kotlin.gradle.dsl.JvmTarget
import org.jetbrains.kotlin.gradle.dsl.KotlinVersion
import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

plugins {
    alias(libs.plugins.kotlin)
    alias(libs.plugins.intelliJPlatForm)
    alias(libs.plugins.changelog)
    alias(libs.plugins.kover)
    alias(libs.plugins.kotlinSerialization)
}

group = providers.gradleProperty("pluginGroup").get()
version = providers.gradleProperty("pluginVersion").get()

// Set the JVM language level used to build the project.
kotlin {
    jvmToolchain(21)
}

// Configure project's dependencies
repositories {
    mavenCentral()

    // IntelliJ Platform Gradle Plugin Repositories Extension - read more: https://plugins.jetbrains.com/docs/intellij/tools-intellij-platform-gradle-plugin-repositories-extension.html
    intellijPlatform {
        defaultRepositories()
    }
}

// Dependencies are managed with Gradle version catalog - read more: https://docs.gradle.org/current/userguide/platforms.html#sub:version-catalog
dependencies {
    compileOnly(libs.kotlinxSerialization)

    testImplementation(kotlin("test"))
    testImplementation(libs.junit)

    // IntelliJ Platform Gradle Plugin Dependencies Extension - read more: https://plugins.jetbrains.com/docs/intellij/tools-intellij-platform-gradle-plugin-dependencies-extension.html
    intellijPlatform {
        pycharm(providers.gradleProperty("platformVersion"))

        // Plugin Dependencies. Uses `platformBundledPlugins` property from the gradle.properties file for bundled IntelliJ Platform plugins.
        bundledPlugins(providers.gradleProperty("platformBundledPlugins").map { it.split(',') })
        plugins(providers.gradleProperty("platformPlugins").map { it.split(',') })

        pluginVerifier()
        zipSigner()
        testFramework(TestFrameworkType.Platform)
    }
}

// Configure IntelliJ Platform Gradle Plugin - read more: https://plugins.jetbrains.com/docs/intellij/tools-intellij-platform-gradle-plugin-extension.html
intellijPlatform {
    pluginConfiguration {
        name = providers.gradleProperty("pluginName")
        version = providers.gradleProperty("pluginVersion")

        // Extract the <!-- Plugin description --> section from README.md and provide for the plugin's manifest
        description = providers.fileContents(layout.projectDirectory.file("README.md")).asText.map {
            val start = "<!-- Plugin description -->"
            val end = "<!-- Plugin description end -->"

            with(it.lines()) {
                if (!containsAll(listOf(start, end))) {
                    throw GradleException("Plugin description section not found in README.md:\n$start ... $end")
                }
                subList(indexOf(start) + 1, indexOf(end)).joinToString("\n").let(::markdownToHTML)
            }
        }

        // The change notes are the changelog section of this version, or Unreleased for prereleases. The changelog plugin
        // can't read it: git-cliff writes a heading per scope, like "#### PyCharm", below the one per type.
        changeNotes = providers.fileContents(layout.projectDirectory.file("../CHANGELOG.md")).asText
            .zip(providers.gradleProperty("pluginVersion")) { changelog, pluginVersion ->
                val lines = changelog.lines()
                val start = lines.indexOfFirst { it.startsWith("## [$pluginVersion]") }.takeIf { it >= 0 }
                    ?: lines.indexOfFirst { it.startsWith("## [Unreleased]") }.takeIf { it >= 0 }
                    ?: throw GradleException("Neither $pluginVersion nor Unreleased found in CHANGELOG.md")
                val section = lines.drop(start + 1).takeWhile { !it.startsWith("## ") }
                val notes = markdownToHTML(section.joinToString("\n"))

                // the Marketplace rejects longer change notes; then only the subject lines of what users notice
                val maxLength = 65535
                if (notes.length <= maxLength) {
                    notes
                } else {
                    val fullList = if (lines[start].startsWith("## [Unreleased]")) {
                        "https://github.com/robotcodedev/robotcode/commits/main"
                    } else {
                        "https://github.com/robotcodedev/robotcode/blob/main/CHANGELOG.md"
                    }
                    val footer = markdownToHTML(
                        "This list shows only the features, bug fixes and performance improvements. " +
                            "See the [full list of changes]($fullList).",
                    )
                    // each subject line with the headings of its type and its scope; git-cliff writes the type headings
                    // with an ordering prefix, like "### <!-- 0 -->Features", and subject lines without indentation
                    var type = ""
                    var scope: String? = null
                    val subjects = buildList {
                        for (line in section) {
                            when {
                                line.startsWith("### ") -> {
                                    type = line
                                    scope = null
                                }
                                line.startsWith("#### ") -> scope = line
                                line.startsWith("- ") &&
                                    type.substringAfter("-->").trim() in listOf("Features", "Bug Fixes", "Performance") ->
                                    add(Triple(type, scope, line))
                            }
                        }
                    }

                    generateSequence(subjects.size) { it - 1 }
                        .takeWhile { it >= 0 }
                        .map { count ->
                            val outline = buildList {
                                var lastType: String? = null
                                var lastScope: String? = null
                                for ((subjectType, subjectScope, subject) in subjects.take(count)) {
                                    if (subjectType != lastType) {
                                        add(subjectType)
                                        lastType = subjectType
                                        lastScope = null
                                    }
                                    if (subjectScope != lastScope) {
                                        subjectScope?.let(::add)
                                        lastScope = subjectScope
                                    }
                                    add(subject)
                                }
                            }
                            markdownToHTML(outline.joinToString("\n")) + footer
                        }
                        .first { it.length <= maxLength }
                }
            }

        ideaVersion {
            sinceBuild = providers.gradleProperty("pluginSinceBuild")
            untilBuild = providers.gradleProperty("pluginUntilBuild")
        }
    }

    signing {
        certificateChain = providers.environmentVariable("CERTIFICATE_CHAIN")
        privateKey = providers.environmentVariable("PRIVATE_KEY")
        password = providers.environmentVariable("PRIVATE_KEY_PASSWORD")
    }

    publishing {
        token = providers.environmentVariable("PUBLISH_TOKEN")

        // The pluginVersion is based on the SemVer (https://semver.org) and supports pre-release labels, like 2.1.7-alpha.3
        // Specify pre-release label to publish the plugin in a custom Release Channel automatically. Read more:
        // https://plugins.jetbrains.com/docs/intellij/deployment.html#specifying-a-release-channel
        channels = providers.gradleProperty("pluginVersion")
            .map { listOf(it.substringAfter('-', "").substringBefore('.').ifEmpty { "default" }) }
    }

    pluginVerification {
        failureLevel = listOf(INVALID_PLUGIN, COMPATIBILITY_PROBLEMS, MISSING_DEPENDENCIES)
        verificationReportsFormats = listOf(MARKDOWN, PLAIN)

        // released IDE versions by default; -PverifyEap checks the current EAP build instead, with reports of their own
        val eap = providers.gradleProperty("verifyEap").isPresent
        if (eap) {
            verificationReportsDirectory = layout.buildDirectory.dir("reports/pluginVerifier-eap")
        }
        ides {
            val filter: ProductReleasesFilterParameters.() -> Unit = {
                types = listOf(IntelliJPlatformType.PyCharm)
                channels = listOf(if (eap) ProductRelease.Channel.EAP else ProductRelease.Channel.RELEASE)
                sinceBuild = providers.gradleProperty("pluginSinceBuild")
                untilBuild = providers.gradleProperty("pluginUntilBuild")
            }
            // only the newest EAP build: select would also return the last EAP build of every released version
            if (eap) latest(filter) else select(filter)
        }
    }
}

// Configure Gradle Changelog Plugin - read more: https://github.com/JetBrains/gradle-changelog-plugin
changelog {
    path.set(file("../CHANGELOG.md").canonicalPath)
    groups.empty()
    repositoryUrl = providers.gradleProperty("pluginRepositoryUrl")
}

// Configure Gradle Kover Plugin - read more: https://github.com/Kotlin/kotlinx-kover#configuration
kover {
    reports {
        total {
            xml {
                onCheck = true
            }
        }
    }
}

val prepareSandboxConfig: PrepareSandboxTask.() -> Unit = {
    from("..") {
        include("package.json", "language-configuration.json", "syntaxes/**/*", "bundled/**/*")
        exclude("**/bin")
        exclude("**/__pycache__")
        // the Markdown code block injection is only used by VS Code
        exclude("syntaxes/codeblock_robotframework.tmLanguage.json", "syntaxes/robotframework-markdown.tmLanguage.json")
        into("robotcode4ij/data")
    }
}

tasks {
    runIde {

        // From https://app.slack.com/client/T5P9YATH9/C5U8BM1MK
        // systemProperty("ide.experimental.ui", "true")
        // systemProperty("projectView.hide.dot.idea", "false")
        // systemProperty("terminal.new.ui", "false")
        // systemProperty("ide.tree.painter.compact.default", "true")
    }

    wrapper {
        gradleVersion = providers.gradleProperty("gradleVersion").get()
    }

    publishPlugin {
        dependsOn(patchChangelog)
    }

    withType<PrepareSandboxTask>().configureEach(prepareSandboxConfig)
}


tasks.withType<KotlinCompile> {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_21)
        languageVersion.set(KotlinVersion.KOTLIN_2_3)
        apiVersion.set(KotlinVersion.KOTLIN_2_3)
    }
}

// the IDE version that the runIde* tasks below start instead of their own, a release such as -PrunIdeVersion=2026.2.3
// or an EAP build number; the plugin is still built against platformVersion
val runIdeVersion: String? = providers.gradleProperty("runIdeVersion").orNull

// starts the task's IDE in runIdeVersion, when given, with a sandbox of its own for that version, because the default
// sandbox belongs to platformVersion
fun IntelliJPlatformTestingExtension.RunIdeParameters.applyRunIdeVersion() {
    runIdeVersion?.let {
        version = it
        sandboxDirectory = intellijPlatform.sandboxContainer.dir("${project.name}/PY-$it")
    }
}

// Configure UI tests plugin
// Read more: https://github.com/JetBrains/intellij-ui-test-robot
intellijPlatformTesting.runIde.register("runIdeForUiTests") {
    applyRunIdeVersion()

    task {
        jvmArgumentProviders += CommandLineArgumentProvider {
            listOf(
                "-Drobot-server.port=8082",
                "-Dide.mac.message.dialogs.as.sheets=false",
                "-Djb.privacy.policy.text=<!--999.999-->",
                "-Djb.consents.confirmation.enabled=false",
            )
        }
    }

    plugins {
        robotServerPlugin(Constraints.LATEST_VERSION)
    }
}

intellijPlatformTesting.runIde.register("runIdePyCharmProf") {
    type = IntelliJPlatformType.PyCharmProfessional
    applyRunIdeVersion()
}

intellijPlatformTesting.runIde.register("runIdePyCharmCommunityEAP") {
    type = IntelliJPlatformType.PyCharmCommunity
    version = "LATEST-EAP-SNAPSHOT"
    applyRunIdeVersion()
}

intellijPlatformTesting.runIde.register("runIdeIntellijIdeaC") {
    type = IntelliJPlatformType.IntellijIdeaCommunity
    applyRunIdeVersion()
    plugins {
        // the fixed Python plugin only fits platformVersion; another IDE version gets the newest compatible one
        if (runIdeVersion != null) {
            compatiblePlugin("PythonCore")
        } else {
            plugin("PythonCore:261.22158.182")
        }
    }
}

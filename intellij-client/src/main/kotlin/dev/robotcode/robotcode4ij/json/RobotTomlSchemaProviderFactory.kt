package dev.robotcode.robotcode4ij.json

import com.intellij.openapi.project.DumbAware
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.jetbrains.jsonSchema.extension.JsonSchemaFileProvider
import com.jetbrains.jsonSchema.extension.JsonSchemaProviderFactory
import com.jetbrains.jsonSchema.extension.SchemaType
import com.jetbrains.jsonSchema.impl.JsonSchemaVersion
import com.jetbrains.jsonSchema.remote.JsonFileResolver

/** RobotCode's JSON schema for `robot.toml`, the one VS Code gets through `tomlValidation` in package.json. */
const val ROBOT_TOML_SCHEMA_URL = "https://www.robotcode.io/schemas/robot.toml.json"

private val ROBOT_TOML_FILE_NAMES = setOf("robot.toml", ".robot.toml")

/**
 * Gives `robot.toml` and `.robot.toml` RobotCode's JSON schema, which the IDE downloads once and completes their
 * settings from.
 */
class RobotTomlSchemaProviderFactory : JsonSchemaProviderFactory, DumbAware {
    override fun getProviders(project: Project): List<JsonSchemaFileProvider> = listOf(RobotTomlSchemaFileProvider)
}

private object RobotTomlSchemaFileProvider : JsonSchemaFileProvider {
    override fun isAvailable(file: VirtualFile): Boolean = file.name in ROBOT_TOML_FILE_NAMES

    // the status bar shows it as "Schema: robot.toml"
    override fun getName(): String = "robot.toml"

    override fun getSchemaFile(): VirtualFile? = JsonFileResolver.urlToFile(ROBOT_TOML_SCHEMA_URL)

    override fun getSchemaType(): SchemaType = SchemaType.remoteSchema

    override fun getSchemaVersion(): JsonSchemaVersion = JsonSchemaVersion.SCHEMA_7

    override fun getRemoteSource(): String = ROBOT_TOML_SCHEMA_URL
}

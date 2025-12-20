"""build.gradle generation for Gradle build tool (STUB - Not yet implemented).

This module will generate build.gradle files (Groovy DSL) from normalized scenarios.

Implementation TODO:
- Convert scenario dependencies to Maven coordinates
- Generate Gradle dependency DSL syntax
- Support different configurations (implementation, api, etc.)
- Handle dependency locking configuration
- Optional: Support build.gradle.kts (Kotlin DSL)
"""

from typing import List, Optional


def generate_build_gradle(
    group: str,
    name: str,
    version: str,
    dependencies: List[str],
    repositories: Optional[List[str]] = None,
    use_kotlin_dsl: bool = False
) -> str:
    """Generate build.gradle content for Gradle (STUB).

    Args:
        group: Maven group ID (e.g., 'com.example')
        name: Project name
        version: Project version
        dependencies: List of Maven coordinates (group:artifact:version)
        repositories: Optional list of repository URLs
        use_kotlin_dsl: Generate build.gradle.kts instead of build.gradle

    Returns:
        Complete build.gradle file content as a string

    Raises:
        NotImplementedError: This is a stub implementation
    """
    raise NotImplementedError(
        "build.gradle generation is not yet implemented. "
        "See src/bom_bench/generators/gradle/build_gradle.py for implementation guide."
    )

    # TODO: Implementation outline:
    # 1. Generate plugins block (if needed)
    # 2. Generate repositories block with Maven Central + custom repos
    # 3. Generate dependencies block:
    #    dependencies {
    #        implementation 'group:artifact:version'
    #        testImplementation 'junit:junit:4.13.2'
    #    }
    # 4. Add dependency locking configuration:
    #    dependencyLocking {
    #        lockAllConfigurations()
    #    }
    # 5. Return formatted Groovy DSL string
    # 6. If use_kotlin_dsl: Convert to Kotlin DSL syntax

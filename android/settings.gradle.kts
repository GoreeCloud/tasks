pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories { google(); mavenCentral() }
}
rootProject.name = "GoreeCloudTasks"
include(":app")
includeBuild("../vendor/gc-ui/compose-multiplatform") {
    dependencySubstitution { substitute(module("com.goreecloud.ui:shared-compose")).using(project(":gc-ui-compose")) }
}
includeBuild("../vendor/gc-ui/android/material3-expressive") {
    dependencySubstitution { substitute(module("com.goreecloud.ui:android-expressive")).using(project(":gc-ui-compose")) }
}

package com.goreecloud.tasks

import java.io.File

/** One synthetic fixture shared by native Android, Linux and browser tests. */
internal object PortableFixture {
    fun read(name: String = "schema1-synthetic.json"): ByteArray {
        require(name in setOf("schema1-synthetic.json", "schema2-synthetic.json", "schema3-synthetic.json", "schema4-proposed-synthetic.json", "timestamp-contract.json"))
        val candidates = listOf(
            "fixtures/portable/$name",
            "../fixtures/portable/$name",
            "../../fixtures/portable/$name"
        )
        val file = candidates.map(::File).firstOrNull { it.isFile }
            ?: throw AssertionError(
                "Shared portable backup test fixture unavailable (working directory: " +
                    System.getProperty("user.dir") + ")"
            )
        return file.readBytes()
    }
}

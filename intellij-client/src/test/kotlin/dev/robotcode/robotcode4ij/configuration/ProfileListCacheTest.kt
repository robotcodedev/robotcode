package dev.robotcode.robotcode4ij.configuration

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ProfileListCacheTest {

    private val list = ProfileList(listOf(ProfileInfo("ci"), ProfileInfo("dev")))

    @Test
    fun aClearedCacheReadsAgainAndAFilledOneDoesNot() = runBlocking {
        var reads = 0
        val cache = ProfileListCache(this) {
            reads++
            ProfileListResult.Read(list)
        }

        cache.readInBackground()?.join()
        assertEquals(list, cache.cached)
        assertNull(cache.readInBackground())
        assertEquals(1, reads)

        cache.clear()
        assertNull(cache.cached)
        cache.readInBackground()?.join()
        assertEquals(list, cache.cached)
        assertEquals(2, reads)
    }

    @Test
    fun readingAgainReplacesAFilledList() = runBlocking {
        val lists = mutableListOf(list, ProfileList(listOf(ProfileInfo("staging"))))
        val cache = ProfileListCache(this) { ProfileListResult.Read(lists.removeAt(0)) }

        cache.readInBackground()?.join()
        assertEquals(list, cache.cached)
        cache.reload()?.join()
        assertEquals(listOf("staging"), cache.cached?.profiles?.map { it.name })
    }

    @Test
    fun aListThatCouldNotBeReadIsNotCached() = runBlocking {
        val results = mutableListOf(null, ProfileListResult.Error("broken"), ProfileListResult.Read(list))
        val cache = ProfileListCache(this) { results.removeAt(0) }

        cache.readInBackground()?.join()
        assertNull(cache.cached)
        cache.readInBackground()?.join()
        assertNull(cache.cached)
        cache.readInBackground()?.join()
        assertEquals(list, cache.cached)
    }

    @Test
    fun aReadThatAClearOvertookIsDropped() = runBlocking {
        val answer = CompletableDeferred<ProfileListResult?>()
        val cache = ProfileListCache(this) { answer.await() }

        val reading = cache.readInBackground()
        cache.clear()
        answer.complete(ProfileListResult.Read(list))
        reading?.join()

        assertNull(cache.cached)
    }
}

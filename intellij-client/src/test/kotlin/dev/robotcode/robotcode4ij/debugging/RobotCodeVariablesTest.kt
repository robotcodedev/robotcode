package dev.robotcode.robotcode4ij.debugging

import org.eclipse.lsp4j.debug.VariablesArgumentsFilter.INDEXED
import org.eclipse.lsp4j.debug.VariablesArgumentsFilter.NAMED
import org.junit.Assert.assertEquals
import org.junit.Test

class RobotCodeVariablesTest {

    @Test
    fun aShortListGetsLenAndAllItemsAtOnce() {
        assertEquals(
            ChildrenPlan(listOf(VariablesRequest(NAMED), VariablesRequest(INDEXED, 0, 3)), 3, 0),
            planChildren(indexedVariables = 3)
        )
    }

    @Test
    fun aLongListGetsItsItemsInPagesOf100() {
        assertEquals(
            ChildrenPlan(listOf(VariablesRequest(NAMED), VariablesRequest(INDEXED, 0, 100)), 100, 200),
            planChildren(indexedVariables = 300)
        )
        assertEquals(
            ChildrenPlan(listOf(VariablesRequest(INDEXED, 100, 100)), 200, 100),
            planChildren(indexedVariables = 300, start = 100)
        )
        assertEquals(
            ChildrenPlan(listOf(VariablesRequest(INDEXED, 200, 100)), 300, 0),
            planChildren(indexedVariables = 300, start = 200)
        )
    }

    @Test
    fun aDictionaryIsRequestedWithoutAFilter() {
        // the debugger reports its entries as named children only
        assertEquals(ChildrenPlan(listOf(VariablesRequest()), 0, 0), planChildren(indexedVariables = 0))
    }

    @Test
    fun aScopeIsRequestedWithoutAFilter() {
        // the debugger sends no counts for a scope
        assertEquals(ChildrenPlan(listOf(VariablesRequest()), 0, 0), planChildren())
    }

    @Test
    fun pythonTypesAreShownByTheirClassName() {
        assertEquals("str", typeName("<class 'str'>"))
        assertEquals("list", typeName("<class 'list'>"))
        assertEquals("DotDict", typeName("<class 'robot.utils.dotdict.DotDict'>"))
        assertEquals("int", typeName("int"))
        assertEquals(null, typeName(null))
    }
}

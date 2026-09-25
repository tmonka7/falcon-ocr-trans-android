package com.falcon.ocrtrans.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

/** Covers language-code parsing, including the jp/ja trap. */
public class LangTest {

    @Test
    public void parsesCanonicalCodes() {
        assertEquals(Lang.EN, Lang.fromCode("en"));
        assertEquals(Lang.KO, Lang.fromCode("ko"));
        assertEquals(Lang.JA, Lang.fromCode("ja"));
        assertEquals(Lang.ZH, Lang.fromCode("zh"));
    }

    /**
     * {@code jp} is a country code, not a language code, but it is a common
     * enough mistake that it has to keep resolving.
     */
    @Test
    public void acceptsJpAsAliasForJa() {
        assertEquals(Lang.JA, Lang.fromCode("jp"));
        assertEquals("ja", Lang.fromCode("jp").code());
    }

    @Test
    public void stripsRegionSuffixes() {
        assertEquals(Lang.ZH, Lang.fromCode("zh-Hans"));
        assertEquals(Lang.EN, Lang.fromCode("en_US"));
        assertEquals(Lang.KO, Lang.fromCode("KO-kr"));
    }

    @Test
    public void unknownCodeIsNull() {
        assertNull(Lang.fromCode("de"));
        assertNull(Lang.fromCode(null));
    }

    @Test
    public void fallbackIsUsedForUnknownCodes() {
        assertEquals(Lang.ZH, Lang.fromCodeOr("de", Lang.ZH));
        assertEquals(Lang.KO, Lang.fromCodeOr(null, Lang.KO));
        assertEquals(Lang.JA, Lang.fromCodeOr("jp", Lang.KO));
    }

    @Test
    public void pairKeyMatchesModelDirectoryNaming() {
        assertEquals("en-ko", Lang.pairKey(Lang.EN, Lang.KO));
        assertEquals("ja-zh", Lang.pairKey(Lang.JA, Lang.ZH));
    }

    /**
     * Korean is implemented but withheld from the interface. It must keep
     * parsing — stored data and model paths depend on it — while never being
     * offered, restored from preferences, or listed.
     */
    @Test
    public void koreanIsImplementedButNotUserFacing() {
        assertEquals(Lang.KO, Lang.fromCode("ko"));
        assertFalse(Lang.KO.isUserFacing());
        for (Lang l : Lang.userFacing()) {
            assertTrue(l != Lang.KO);
        }
        assertEquals(Lang.EN, Lang.userFacingOr("ko", Lang.EN));
    }

    @Test
    public void userFacingLanguagesSurviveTheFilter() {
        assertTrue(Lang.EN.isUserFacing());
        assertTrue(Lang.JA.isUserFacing());
        assertTrue(Lang.ZH.isUserFacing());
        assertEquals(Lang.JA, Lang.userFacingOr("jp", Lang.EN));
        assertEquals(Lang.ZH, Lang.userFacingOr("de", Lang.ZH));
    }
}

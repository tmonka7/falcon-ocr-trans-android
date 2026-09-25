package com.falcon.ocrtrans.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;

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
}

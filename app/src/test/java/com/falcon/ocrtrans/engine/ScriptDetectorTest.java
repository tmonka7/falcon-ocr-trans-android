package com.falcon.ocrtrans.engine;

import static org.junit.Assert.assertEquals;

import com.falcon.ocrtrans.core.Lang;

import org.junit.Test;

/** Covers the script heuristic that decides which recognition head to trust. */
public class ScriptDetectorTest {

    @Test
    public void hangulIsKorean() {
        assertEquals(Lang.KO, ScriptDetector.detect("안녕하세요", Lang.EN));
    }

    @Test
    public void kanaIsJapanese() {
        assertEquals(Lang.JA, ScriptDetector.detect("こんにちは", Lang.EN));
    }

    @Test
    public void hanWithoutKanaIsChinese() {
        assertEquals(Lang.ZH, ScriptDetector.detect("你好世界", Lang.EN));
    }

    @Test
    public void latinIsEnglish() {
        assertEquals(Lang.EN, ScriptDetector.detect("Hello world", Lang.ZH));
    }

    /**
     * Kana is the tiebreaker for text that is mostly shared Han characters —
     * this is the case the whole heuristic exists to handle.
     */
    @Test
    public void mixedHanAndKanaIsJapanese() {
        assertEquals(Lang.JA, ScriptDetector.detect("東京に行く", Lang.ZH));
    }

    /** Hangul settles it even when Latin dominates the character count. */
    @Test
    public void smallHangulShareStillWins() {
        assertEquals(Lang.KO, ScriptDetector.detect("WiFi 비밀번호", Lang.EN));
    }

    @Test
    public void digitsAndPunctuationFallBack() {
        assertEquals(Lang.ZH, ScriptDetector.detect("12345 !!! ???", Lang.ZH));
    }

    @Test
    public void nullAndEmptyFallBack() {
        assertEquals(Lang.JA, ScriptDetector.detect(null, Lang.JA));
        assertEquals(Lang.JA, ScriptDetector.detect("", Lang.JA));
    }

    /**
     * Documents the known limitation: Japanese written purely in Kanji, such as
     * a two-character sign, is indistinguishable from Chinese by script alone.
     */
    @Test
    public void pureKanjiJapaneseIsReportedAsChinese() {
        assertEquals(Lang.ZH, ScriptDetector.detect("出口", Lang.EN));
    }
}

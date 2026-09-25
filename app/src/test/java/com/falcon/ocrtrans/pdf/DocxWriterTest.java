package com.falcon.ocrtrans.pdf;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

/** Covers the minimal OOXML package written for the PDF-to-DOCX export. */
public class DocxWriterTest {

    @Rule
    public TemporaryFolder folder = new TemporaryFolder();

    private String documentXml(File docx) throws Exception {
        try (ZipFile zip = new ZipFile(docx)) {
            ZipEntry entry = zip.getEntry("word/document.xml");
            assertNotNull("package is missing word/document.xml", entry);
            try (InputStream in = zip.getInputStream(entry);
                 ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] buf = new byte[4096];
                int n;
                while ((n = in.read(buf)) > 0) {
                    out.write(buf, 0, n);
                }
                return out.toString(StandardCharsets.UTF_8.name());
            }
        }
    }

    /** Word refuses to open the package if any of the four parts is absent. */
    @Test
    public void writesEveryRequiredPart() throws Exception {
        File out = folder.newFile("a.docx");
        DocxWriter.write(out, Arrays.asList("hello"));

        Set<String> names = new HashSet<>();
        try (ZipFile zip = new ZipFile(out)) {
            zip.stream().forEach(e -> names.add(e.getName()));
        }
        assertTrue(names.contains("[Content_Types].xml"));
        assertTrue(names.contains("_rels/.rels"));
        assertTrue(names.contains("word/_rels/document.xml.rels"));
        assertTrue(names.contains("word/document.xml"));
    }

    @Test
    public void writesOneParagraphPerEntry() throws Exception {
        File out = folder.newFile("b.docx");
        DocxWriter.write(out, Arrays.asList("first", "second", "third"));

        String xml = documentXml(out);
        assertEquals(3, xml.split("<w:p>", -1).length - 1);
        assertTrue(xml.contains("first"));
        assertTrue(xml.contains("third"));
    }

    /** XML metacharacters in OCR output must not break the package. */
    @Test
    public void escapesXmlMetacharacters() throws Exception {
        File out = folder.newFile("c.docx");
        DocxWriter.write(out, Arrays.asList("a < b & c > d \" e ' f"));

        String xml = documentXml(out);
        assertTrue(xml.contains("&lt;"));
        assertTrue(xml.contains("&amp;"));
        assertTrue(xml.contains("&gt;"));
        assertTrue(xml.contains("&quot;"));
        assertTrue(xml.contains("&apos;"));
        assertFalse("raw ampersand would corrupt the document", xml.contains("b & c"));
    }

    /**
     * A stray control byte from OCR makes Word report the whole file as corrupt,
     * so it has to be dropped rather than escaped.
     */
    @Test
    public void stripsControlCharacters() throws Exception {
        File out = folder.newFile("d.docx");
        DocxWriter.write(out, Arrays.asList("oktexthere"));

        String xml = documentXml(out);
        assertTrue(xml.contains("oktexthere"));
        assertFalse(xml.contains(""));
        assertFalse(xml.contains(""));
    }

    @Test
    public void newlinesBecomeLineBreaks() throws Exception {
        File out = folder.newFile("e.docx");
        DocxWriter.write(out, Arrays.asList("line one\nline two"));

        String xml = documentXml(out);
        assertTrue(xml.contains("<w:br/>"));
        assertTrue(xml.contains("line one"));
        assertTrue(xml.contains("line two"));
    }

    /** Leading and trailing spaces matter for indented source text. */
    @Test
    public void preservesSignificantWhitespace() throws Exception {
        File out = folder.newFile("f.docx");
        DocxWriter.write(out, Arrays.asList("   indented"));
        assertTrue(documentXml(out).contains("xml:space=\"preserve\""));
    }

    @Test
    public void handlesCjkText() throws Exception {
        File out = folder.newFile("g.docx");
        DocxWriter.write(out, Arrays.asList("欢迎 안녕 こんにちは"));

        String xml = documentXml(out);
        assertTrue(xml.contains("欢迎"));
        assertTrue(xml.contains("안녕"));
    }

    @Test
    public void emptyDocumentIsStillValid() throws Exception {
        File out = folder.newFile("h.docx");
        DocxWriter.write(out, java.util.Collections.emptyList());
        assertTrue(documentXml(out).contains("<w:body></w:body>"));
    }
}

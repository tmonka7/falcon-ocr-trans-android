package com.falcon.ocrtrans.pdf;

import androidx.annotation.NonNull;

import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

/**
 * Writes a minimal but valid {@code .docx}.
 *
 * <p>A Word document is an OOXML package — a ZIP holding a content-type map, a
 * relationship graph and the document body. Only the four parts Word actually
 * requires to open a file are emitted here; there is no styling beyond
 * paragraphs, which is all the PDF text export needs. Bringing in a full OOXML
 * library for this would add megabytes to an APK that is already asset-heavy.
 */
public final class DocxWriter {

    private static final String CONTENT_TYPES =
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                    + "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
                    + "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
                    + "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
                    + "<Override PartName=\"/word/document.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/>"
                    + "</Types>";

    private static final String ROOT_RELS =
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                    + "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
                    + "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"word/document.xml\"/>"
                    + "</Relationships>";

    private static final String DOC_RELS =
            "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
                    + "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"/>";

    private static final String W_NS =
            "http://schemas.openxmlformats.org/wordprocessingml/2006/main";

    private DocxWriter() {
    }

    /**
     * @param paragraphs one Word paragraph each; embedded newlines become line
     *                   breaks within the paragraph
     */
    public static void write(@NonNull File target, @NonNull List<String> paragraphs)
            throws IOException {
        try (ZipOutputStream zip = new ZipOutputStream(
                new BufferedOutputStream(new FileOutputStream(target)))) {
            putEntry(zip, "[Content_Types].xml", CONTENT_TYPES);
            putEntry(zip, "_rels/.rels", ROOT_RELS);
            putEntry(zip, "word/_rels/document.xml.rels", DOC_RELS);
            putEntry(zip, "word/document.xml", buildDocument(paragraphs));
        }
    }

    private static String buildDocument(List<String> paragraphs) {
        StringBuilder sb = new StringBuilder(paragraphs.size() * 96);
        sb.append("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>")
                .append("<w:document xmlns:w=\"").append(W_NS).append("\"><w:body>");

        for (String paragraph : paragraphs) {
            sb.append("<w:p><w:r>");
            String[] lines = paragraph.split("\n", -1);
            for (int i = 0; i < lines.length; i++) {
                if (i > 0) {
                    sb.append("<w:br/>");
                }
                // xml:space="preserve" stops Word from trimming leading and
                // trailing spaces, which matters for indented source text.
                sb.append("<w:t xml:space=\"preserve\">")
                        .append(escape(lines[i]))
                        .append("</w:t>");
            }
            sb.append("</w:r></w:p>");
        }

        sb.append("</w:body></w:document>");
        return sb.toString();
    }

    /**
     * Escapes XML metacharacters and drops control characters.
     *
     * <p>OCR output can contain stray control bytes, and a single one of those
     * makes the whole package unreadable — Word reports it as corrupt rather
     * than skipping the character.
     */
    private static String escape(String text) {
        StringBuilder sb = new StringBuilder(text.length() + 16);
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            switch (c) {
                case '&':
                    sb.append("&amp;");
                    break;
                case '<':
                    sb.append("&lt;");
                    break;
                case '>':
                    sb.append("&gt;");
                    break;
                case '"':
                    sb.append("&quot;");
                    break;
                case '\'':
                    sb.append("&apos;");
                    break;
                default:
                    if (c == '\t' || c >= 0x20) {
                        sb.append(c);
                    }
                    break;
            }
        }
        return sb.toString();
    }

    private static void putEntry(ZipOutputStream zip, String name, String content)
            throws IOException {
        zip.putNextEntry(new ZipEntry(name));
        OutputStream out = zip;
        out.write(content.getBytes(StandardCharsets.UTF_8));
        zip.closeEntry();
    }
}

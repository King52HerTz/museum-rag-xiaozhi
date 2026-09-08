package xiaozhi.modules.museum;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.server.ResponseStatusException;

import xiaozhi.common.exception.RenException;
import xiaozhi.modules.museum.service.MuseumExhibitAssetService;

class MuseumExhibitAssetServiceTest {
    @TempDir
    Path tempDirectory;

    private MuseumExhibitAssetService service;

    @BeforeEach
    void setUp() {
        service = new MuseumExhibitAssetService();
        ReflectionTestUtils.setField(service, "storageDirectory", tempDirectory.toString());
        ReflectionTestUtils.setField(service, "publicBaseUrl", "/xiaozhi/museum/public/v1/assets/");
        ReflectionTestUtils.setField(service, "maxBytes", 8L * 1024 * 1024);
    }

    @Test
    void storesPngWithContentAddressedName() throws Exception {
        byte[] content = new byte[] {(byte) 0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 1, 2, 3};
        String sha256 = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(content));
        MockMultipartFile file = new MockMultipartFile("file", "artifact.png", "image/png", content);

        Map<String, String> result = service.store(file);

        assertEquals(sha256, result.get("imageSha256"));
        assertEquals("/xiaozhi/museum/public/v1/assets/" + sha256 + ".png", result.get("imageUrl"));
        assertTrue(Files.exists(tempDirectory.resolve(sha256 + ".png")));
    }

    @Test
    void rejectsFileWhoseContentIsNotAnImage() {
        MockMultipartFile file = new MockMultipartFile("file", "fake.png", "image/png", "not an image".getBytes());

        assertThrows(RenException.class, () -> service.store(file));
    }

    @Test
    void rejectsOversizedImage() {
        ReflectionTestUtils.setField(service, "maxBytes", 7L);
        MockMultipartFile file = new MockMultipartFile("file", "large.png", "image/png",
                new byte[] {(byte) 0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a});

        assertThrows(RenException.class, () -> service.store(file));
    }

    @Test
    void rejectsUnsafeAssetName() {
        assertThrows(ResponseStatusException.class, () -> service.load("../secret.png"));
    }
}

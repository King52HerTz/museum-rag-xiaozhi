package xiaozhi.modules.museum.service;

import java.io.IOException;
import java.nio.file.FileAlreadyExistsException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Map;
import java.util.regex.Pattern;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import xiaozhi.common.exception.RenException;

@Service
public class MuseumExhibitAssetService {
    private static final Pattern SAFE_FILE_NAME = Pattern.compile("^[0-9a-f]{64}\\.(jpg|png|webp)$");

    @Value("${museum.assets.directory:data/museum/exhibits}")
    private String storageDirectory;

    @Value("${museum.assets.public-base-url:/xiaozhi/museum/public/v1/assets}")
    private String publicBaseUrl;

    @Value("${museum.assets.max-bytes:8388608}")
    private long maxBytes;

    public Map<String, String> store(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new RenException("请选择要上传的展品图片");
        }
        if (file.getSize() > maxBytes) {
            throw new RenException("展品图片不能超过 8 MB");
        }

        try {
            byte[] content = file.getBytes();
            if (content.length > maxBytes) {
                throw new RenException("展品图片不能超过 8 MB");
            }
            String extension = detectExtension(content);
            String sha256 = sha256(content);
            String fileName = sha256 + "." + extension;
            Path directory = rootDirectory();
            Files.createDirectories(directory);
            Path target = directory.resolve(fileName);
            try {
                Files.write(target, content, StandardOpenOption.CREATE_NEW);
            } catch (FileAlreadyExistsException ignored) {
                if (!Files.isRegularFile(target, LinkOption.NOFOLLOW_LINKS)) {
                    throw new RenException("展品图片存储位置异常");
                }
            }
            return Map.of(
                    "imageUrl", publicUrl(fileName),
                    "imageSha256", sha256);
        } catch (IOException e) {
            throw new RenException("保存展品图片失败", e);
        }
    }

    public Resource load(String fileName) {
        if (fileName == null || !SAFE_FILE_NAME.matcher(fileName).matches()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "展品图片不存在");
        }
        Path path = rootDirectory().resolve(fileName).normalize();
        if (!path.startsWith(rootDirectory()) || !Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "展品图片不存在");
        }
        return new FileSystemResource(path);
    }

    public String contentType(String fileName) {
        if (fileName.endsWith(".png")) {
            return "image/png";
        }
        if (fileName.endsWith(".webp")) {
            return "image/webp";
        }
        return "image/jpeg";
    }

    private Path rootDirectory() {
        return Path.of(storageDirectory).toAbsolutePath().normalize();
    }

    private String publicUrl(String fileName) {
        return publicBaseUrl.replaceAll("/+$", "") + "/" + fileName;
    }

    private String detectExtension(byte[] content) {
        if (content.length >= 8
                && (content[0] & 0xff) == 0x89 && content[1] == 0x50 && content[2] == 0x4e && content[3] == 0x47
                && content[4] == 0x0d && content[5] == 0x0a && content[6] == 0x1a && content[7] == 0x0a) {
            return "png";
        }
        if (content.length >= 3 && (content[0] & 0xff) == 0xff && (content[1] & 0xff) == 0xd8
                && (content[2] & 0xff) == 0xff) {
            return "jpg";
        }
        if (content.length >= 12 && content[0] == 'R' && content[1] == 'I' && content[2] == 'F' && content[3] == 'F'
                && content[8] == 'W' && content[9] == 'E' && content[10] == 'B' && content[11] == 'P') {
            return "webp";
        }
        throw new RenException("仅支持 JPG、PNG 或 WebP 图片");
    }

    private String sha256(byte[] content) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(content));
        } catch (NoSuchAlgorithmException e) {
            throw new RenException("计算展品图片摘要失败", e);
        }
    }
}

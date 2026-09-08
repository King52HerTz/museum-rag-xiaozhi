package xiaozhi.modules.museum.controller;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import lombok.RequiredArgsConstructor;
import xiaozhi.modules.museum.service.MuseumExhibitService;

@RestController
@RequiredArgsConstructor
@RequestMapping("/museum/public/v1")
public class MuseumPublicCatalogController {
    private final MuseumExhibitService exhibitService;

    @Value("${museum.catalog.api-key:}")
    private String apiKey;

    @GetMapping("/catalog")
    public ResponseEntity<Map<String, Object>> catalog(
            @RequestHeader(value = HttpHeaders.AUTHORIZATION, required = false) String authorization,
            @RequestHeader(value = HttpHeaders.IF_NONE_MATCH, required = false) String ifNoneMatch) {
        if (!authorized(authorization)) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        Map<String, Object> catalog = exhibitService.publicCatalog();
        String etag = "\"" + catalog.get("version") + "\"";
        if (etag.equals(ifNoneMatch)) {
            return ResponseEntity.status(HttpStatus.NOT_MODIFIED).eTag(etag).build();
        }
        return ResponseEntity.ok().eTag(etag).header(HttpHeaders.CACHE_CONTROL, "private, max-age=60").body(catalog);
    }

    private boolean authorized(String authorization) {
        if (StringUtils.isBlank(apiKey) || StringUtils.isBlank(authorization) || !authorization.startsWith("Bearer ")) {
            return false;
        }
        byte[] expected = apiKey.getBytes(StandardCharsets.UTF_8);
        byte[] provided = authorization.substring(7).trim().getBytes(StandardCharsets.UTF_8);
        return MessageDigest.isEqual(expected, provided);
    }
}

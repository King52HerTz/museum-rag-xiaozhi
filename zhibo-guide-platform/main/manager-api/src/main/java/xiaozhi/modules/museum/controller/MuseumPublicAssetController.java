package xiaozhi.modules.museum.controller;

import org.springframework.core.io.Resource;
import org.springframework.http.CacheControl;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import lombok.RequiredArgsConstructor;
import xiaozhi.modules.museum.service.MuseumExhibitAssetService;

@RestController
@RequiredArgsConstructor
@RequestMapping("/museum/public/v1/assets")
public class MuseumPublicAssetController {
    private final MuseumExhibitAssetService assetService;

    @GetMapping("/{fileName}")
    public ResponseEntity<Resource> image(@PathVariable String fileName) {
        Resource resource = assetService.load(fileName);
        String sha256 = fileName.substring(0, 64);
        return ResponseEntity.ok()
                .contentType(MediaType.parseMediaType(assetService.contentType(fileName)))
                .cacheControl(CacheControl.maxAge(java.time.Duration.ofDays(365)).cachePublic().immutable())
                .eTag('"' + sha256 + '"')
                .body(resource);
    }
}

package xiaozhi.modules.museum.controller;

import java.util.Map;

import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import xiaozhi.common.page.PageData;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.museum.entity.MuseumExhibitEntity;
import xiaozhi.modules.museum.service.MuseumExhibitService;

@RestController
@RequiredArgsConstructor
@RequestMapping("/museum/exhibits")
@Tag(name = "博物馆展品内容")
public class MuseumExhibitController {
    private final MuseumExhibitService exhibitService;

    @GetMapping
    @Operation(summary = "分页查询展品")
    @RequiresPermissions("sys:role:normal")
    public Result<PageData<MuseumExhibitEntity>> page(@RequestParam Map<String, Object> params) {
        return new Result<PageData<MuseumExhibitEntity>>().ok(exhibitService.page(params));
    }

    @PostMapping
    @Operation(summary = "创建展品草稿")
    @RequiresPermissions("sys:role:normal")
    public Result<MuseumExhibitEntity> create(@RequestBody MuseumExhibitEntity entity) {
        return new Result<MuseumExhibitEntity>().ok(exhibitService.create(entity));
    }

    @PutMapping("/{id}")
    @Operation(summary = "更新展品内容")
    @RequiresPermissions("sys:role:normal")
    public Result<MuseumExhibitEntity> update(@PathVariable String id, @RequestBody MuseumExhibitEntity entity) {
        return new Result<MuseumExhibitEntity>().ok(exhibitService.update(id, entity));
    }

    @PostMapping("/{id}/status/{status}")
    @Operation(summary = "变更展品发布状态")
    @RequiresPermissions("sys:role:normal")
    public Result<MuseumExhibitEntity> changeStatus(@PathVariable String id, @PathVariable String status) {
        return new Result<MuseumExhibitEntity>().ok(exhibitService.changeStatus(id, status.toUpperCase()));
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除未发布展品")
    @RequiresPermissions("sys:role:normal")
    public Result<Void> delete(@PathVariable String id) {
        exhibitService.deleteDraft(id);
        return new Result<>();
    }
}

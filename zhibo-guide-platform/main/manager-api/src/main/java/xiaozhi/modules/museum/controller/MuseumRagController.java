package xiaozhi.modules.museum.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.AllArgsConstructor;
import org.apache.shiro.authz.annotation.RequiresPermissions;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.security.user.SecurityUser;
import xiaozhi.modules.museum.service.MuseumRagService;

import java.util.Map;

@AllArgsConstructor
@RestController
@RequestMapping("/museum/rag")
@Tag(name = "博物馆知识库")
public class MuseumRagController {

    private final MuseumRagService museumRagService;

    @GetMapping("/documents")
    @Operation(summary = "获取博物馆知识库文档列表")
    @RequiresPermissions("sys:role:normal")
    public Result<Object> listDocuments() {
        return new Result<>().ok(museumRagService.listDocuments());
    }

    @PostMapping("/documents/upload")
    @Operation(summary = "上传文档到博物馆知识库")
    @RequiresPermissions("sys:role:normal")
    public Result<Object> uploadDocument(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "museum", required = false) String museum,
            @RequestParam(value = "exhibition", required = false) String exhibition,
            @RequestParam(value = "exhibit_id", required = false) String exhibitId,
            @RequestParam(value = "era", required = false) String era,
            @RequestParam(value = "category", required = false) String category) {
        return new Result<>().ok(museumRagService.uploadDocument(file, museum, exhibition, exhibitId, era, category));
    }

    @GetMapping("/documents/upload/jobs")
    @Operation(summary = "获取博物馆知识库上传任务列表")
    @RequiresPermissions("sys:role:normal")
    public Result<Object> listUploadJobs() {
        return new Result<>().ok(museumRagService.listUploadJobs());
    }

    @GetMapping("/documents/upload/jobs/{jobId}")
    @Operation(summary = "获取博物馆知识库上传任务状态")
    @RequiresPermissions("sys:role:normal")
    public Result<Object> getUploadJob(@PathVariable String jobId) {
        return new Result<>().ok(museumRagService.getUploadJob(jobId));
    }

    @DeleteMapping("/documents/{filename}")
    @Operation(summary = "删除博物馆知识库文档")
    @RequiresPermissions("sys:role:normal")
    public Result<Object> deleteDocument(@PathVariable String filename) {
        return new Result<>().ok(museumRagService.deleteDocument(filename));
    }

    @GetMapping("/documents/delete/jobs/{jobId}")
    @Operation(summary = "获取博物馆知识库删除任务状态")
    @RequiresPermissions("sys:role:normal")
    public Result<Object> getDeleteJob(@PathVariable String jobId) {
        return new Result<>().ok(museumRagService.getDeleteJob(jobId));
    }

    @PostMapping("/query")
    @Operation(summary = "博物馆知识库检索测试")
    @RequiresPermissions("sys:role:normal")
    public Result<Object> query(@RequestBody Map<String, Object> request) {
        return new Result<>().ok(museumRagService.query(request));
    }

    @GetMapping("/workbench-login-url")
    @Operation(summary = "获取博物馆知识库工作台免登录地址")
    @RequiresPermissions("sys:role:normal")
    public Result<Object> getWorkbenchLoginUrl() {
        return new Result<>().ok(museumRagService.getWorkbenchLoginUrl(SecurityUser.getUser()));
    }
}

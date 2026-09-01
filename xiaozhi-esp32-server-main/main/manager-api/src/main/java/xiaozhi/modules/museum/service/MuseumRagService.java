package xiaozhi.modules.museum.service;

import cn.hutool.http.HttpRequest;
import cn.hutool.http.HttpResponse;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.user.UserDetail;

import java.io.File;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import jakarta.annotation.PostConstruct;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

@Slf4j
@Service
public class MuseumRagService {

    private static final String DEFAULT_BRIDGE_SECRET = "museum-rag-bridge-dev-secret";
    private static final String DEFAULT_BRIDGE_API_KEY = "museum-rag-bridge-api-dev-key";
    private static final String DEFAULT_SUPERMEW_USERNAME = "admin";
    private static final String DEFAULT_SUPERMEW_PASSWORD = "123456";

    @Value("${museum-rag.base-url:http://127.0.0.1:8010}")
    private String baseUrl;

    @Value("${museum-rag.workbench-url:http://127.0.0.1:8000}")
    private String workbenchUrl;

    @Value("${museum-rag.username:admin}")
    private String username;

    @Value("${museum-rag.password:123456}")
    private String password;

    @Value("${museum-rag.api-key:museum-rag-bridge-api-dev-key}")
    private String apiKey;

    @Value("${museum-rag.timeout:60000}")
    private int timeout;

    @Value("${museum-rag.bridge-secret:museum-rag-bridge-dev-secret}")
    private String bridgeSecret;

    @Value("${museum-rag.bridge-expire-seconds:60}")
    private long bridgeExpireSeconds;

    private String accessToken;

    @PostConstruct
    public void warnInsecureMuseumRagConfig() {
        StringBuilder warnings = new StringBuilder();
        if (DEFAULT_BRIDGE_SECRET.equals(bridgeSecret)) {
            warnings.append("museum-rag.bridge-secret=dev-default; ");
        }
        if (DEFAULT_SUPERMEW_USERNAME.equals(username)) {
            warnings.append("museum-rag.username=admin; ");
        }
        if (DEFAULT_SUPERMEW_PASSWORD.equals(password)) {
            warnings.append("museum-rag.password=123456; ");
        }
        if (apiKey == null || apiKey.isBlank()) {
            warnings.append("museum-rag.api-key=empty; ");
        } else if (DEFAULT_BRIDGE_API_KEY.equals(apiKey)) {
            warnings.append("museum-rag.api-key=dev-default; ");
        }

        if (warnings.length() > 0) {
            log.warn("Museum RAG is using development defaults, production deployment must override them: {}", warnings);
        }
    }

    public Object listDocuments() {
        return get("/documents");
    }

    public Object listUploadJobs() {
        return get("/documents/upload/jobs");
    }

    public Object getUploadJob(String jobId) {
        return get("/documents/upload/jobs/" + encodePath(jobId));
    }

    public Object uploadDocument(MultipartFile file, String museum, String exhibition) {
        File tempFile = null;
        try {
            if (file == null || file.isEmpty()) {
                throw new RenException("上传文件不能为空");
            }
            String originalFilename = file.getOriginalFilename();
            if (originalFilename == null || originalFilename.trim().isEmpty()) {
                throw new RenException("文件名不能为空");
            }
            tempFile = File.createTempFile("museum-rag-upload-", "-" + originalFilename);
            file.transferTo(tempFile);

            HttpRequest request = HttpRequest.post(url("/documents/upload/async"))
                    .timeout(timeout)
                    .bearerAuth(getAccessToken())
                    .form("file", tempFile, originalFilename);
            if (museum != null && !museum.isBlank()) {
                request.form("museum", museum.trim());
            }
            if (exhibition != null && !exhibition.isBlank()) {
                request.form("exhibition", exhibition.trim());
            }
            HttpResponse response = request.execute();
            return parseResponse(response, "上传文档失败");
        } catch (RenException e) {
            throw e;
        } catch (Exception e) {
            log.error("Upload museum RAG document failed", e);
            throw new RenException("上传文档失败: " + e.getMessage());
        } finally {
            if (tempFile != null && tempFile.exists() && !tempFile.delete()) {
                log.warn("Failed to delete temp upload file: {}", tempFile.getAbsolutePath());
            }
        }
    }

    public Object deleteDocument(String filename) {
        return delete("/documents/delete/async/" + encodePath(filename));
    }

    public Object getDeleteJob(String jobId) {
        return get("/documents/delete/jobs/" + encodePath(jobId));
    }

    public Object query(Map<String, Object> request) {
        if (!request.containsKey("museum")) {
            request.put("museum", "湖南省博物馆");
        }
        if (!request.containsKey("exhibition")) {
            request.put("exhibition", "长沙马王堆汉墓陈列");
        }
        if (!request.containsKey("top_k")) {
            request.put("top_k", 3);
        }
        if (!request.containsKey("need_trace")) {
            request.put("need_trace", true);
        }
        return postBridgeJson("/api/museum/query", request);
    }

    public Map<String, String> getWorkbenchLoginUrl(UserDetail user) {
        if (user == null || user.getId() == null || user.getUsername() == null || user.getUsername().isBlank()) {
            throw new RenException("当前登录用户信息无效，无法进入知识库工作台");
        }

        String ticket = createBridgeTicket(user);
        Map<String, String> result = new HashMap<>();
        result.put("url", buildWorkbenchUrl("/auth/bridge-login") + "?ticket=" + encodeQueryValue(ticket));
        result.put("workbenchUrl", normalizeBaseUrl(workbenchUrl));
        return result;
    }

    private Object get(String path) {
        HttpResponse response = HttpRequest.get(url(path))
                .timeout(timeout)
                .bearerAuth(getAccessToken())
                .execute();
        return parseResponse(response, "请求博物馆知识库失败");
    }

    private Object delete(String path) {
        HttpResponse response = HttpRequest.delete(url(path))
                .timeout(timeout)
                .bearerAuth(getAccessToken())
                .execute();
        return parseResponse(response, "删除博物馆知识库文档失败");
    }

    private Object postJson(String path, Object body) {
        HttpResponse response = HttpRequest.post(url(path))
                .timeout(timeout)
                .bearerAuth(getAccessToken())
                .body(JSONUtil.toJsonStr(body), "application/json")
                .execute();
        return parseResponse(response, "请求博物馆知识库失败");
    }

    private Object postBridgeJson(String path, Object body) {
        String key = apiKey == null ? "" : apiKey.trim();
        if (key.isEmpty()) {
            throw new RenException("博物馆知识库桥接密钥未配置，请设置 museum-rag.api-key");
        }
        HttpResponse response = HttpRequest.post(url(path))
                .timeout(timeout)
                .bearerAuth(key)
                .header("X-Bridge-Trace-Id", "manager-" + System.currentTimeMillis())
                .body(JSONUtil.toJsonStr(body), "application/json")
                .execute();
        return parseResponse(response, "请求博物馆知识库失败");
    }

    private synchronized String getAccessToken() {
        if (accessToken != null && !accessToken.isBlank()) {
            return accessToken;
        }
        return login();
    }

    private synchronized String login() {
        JSONObject payload = JSONUtil.createObj()
                .set("username", username)
                .set("password", password);
        HttpResponse response = HttpRequest.post(url("/auth/login"))
                .timeout(timeout)
                .body(payload.toString(), "application/json")
                .execute();
        Object parsed = parseResponse(response, "登录博物馆知识库失败");
        if (!(parsed instanceof JSONObject json) || json.getStr("access_token") == null) {
            throw new RenException("登录博物馆知识库失败: 未返回 access_token");
        }
        accessToken = json.getStr("access_token");
        return accessToken;
    }

    private Object parseResponse(HttpResponse response, String fallbackMessage) {
        String body = response.body();
        if (response.getStatus() == 401) {
            accessToken = null;
        }
        if (!response.isOk()) {
            String message = fallbackMessage;
            try {
                JSONObject json = JSONUtil.parseObj(body);
                message = json.getStr("detail", json.getStr("message", body));
            } catch (Exception ignored) {
                if (body != null && !body.isBlank()) {
                    message = body;
                }
            }
            throw new RenException(message);
        }
        if (body == null || body.isBlank()) {
            return null;
        }
        try {
            return JSONUtil.parse(body);
        } catch (Exception e) {
            return body;
        }
    }

    private String url(String path) {
        String normalizedBase = normalizeBaseUrl(baseUrl);
        String normalizedPath = path.startsWith("/") ? path : "/" + path;
        return normalizedBase + normalizedPath;
    }

    private String buildWorkbenchUrl(String path) {
        String normalizedBase = normalizeBaseUrl(workbenchUrl);
        String normalizedPath = path.startsWith("/") ? path : "/" + path;
        return normalizedBase + normalizedPath;
    }

    private String normalizeBaseUrl(String value) {
        if (value == null || value.isBlank()) {
            throw new RenException("博物馆知识库地址未配置");
        }
        return value.endsWith("/") ? value.substring(0, value.length() - 1) : value;
    }

    private String encodePath(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8).replace("+", "%20");
    }

    private String encodeQueryValue(String value) {
        return URLEncoder.encode(value, StandardCharsets.UTF_8).replace("+", "%20");
    }

    private String createBridgeTicket(UserDetail user) {
        long now = System.currentTimeMillis() / 1000;
        Map<String, Object> payload = new HashMap<>();
        payload.put("sub", String.valueOf(user.getId()));
        payload.put("username", user.getUsername());
        payload.put("role", isAdmin(user) ? "admin" : "user");
        payload.put("iat", now);
        payload.put("exp", now + bridgeExpireSeconds);
        payload.put("source", "xiaozhi-manager");

        String payloadJson = JSONUtil.toJsonStr(payload);
        String payloadBase64 = java.util.Base64.getUrlEncoder()
                .withoutPadding()
                .encodeToString(payloadJson.getBytes(StandardCharsets.UTF_8));
        String signature = signTicketPayload(payloadBase64);
        return payloadBase64 + "." + signature;
    }

    private boolean isAdmin(UserDetail user) {
        return user.getSuperAdmin() != null && user.getSuperAdmin() == 1;
    }

    private String signTicketPayload(String payloadBase64) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            SecretKeySpec secretKeySpec = new SecretKeySpec(bridgeSecret.getBytes(StandardCharsets.UTF_8), "HmacSHA256");
            mac.init(secretKeySpec);
            byte[] digest = mac.doFinal(payloadBase64.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder(digest.length * 2);
            for (byte b : digest) {
                builder.append(String.format("%02x", b));
            }
            return builder.toString();
        } catch (Exception e) {
            log.error("Create museum bridge ticket failed", e);
            throw new RenException("生成知识库免登录票据失败: " + e.getMessage());
        }
    }
}

package xiaozhi.modules.museum.service.impl;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.fasterxml.jackson.databind.ObjectMapper;

import lombok.RequiredArgsConstructor;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.page.PageData;
import xiaozhi.common.service.impl.BaseServiceImpl;
import xiaozhi.modules.museum.dao.MuseumExhibitDao;
import xiaozhi.modules.museum.entity.MuseumExhibitEntity;
import xiaozhi.modules.museum.service.MuseumExhibitService;

@Service
@RequiredArgsConstructor
public class MuseumExhibitServiceImpl extends BaseServiceImpl<MuseumExhibitDao, MuseumExhibitEntity>
        implements MuseumExhibitService {
    private static final String DRAFT = "DRAFT";
    private static final String PUBLISHED = "PUBLISHED";
    private static final String OFFLINE = "OFFLINE";
    private final ObjectMapper objectMapper;

    @Override
    public PageData<MuseumExhibitEntity> page(Map<String, Object> params) {
        String keyword = String.valueOf(params.getOrDefault("keyword", "")).trim();
        String status = String.valueOf(params.getOrDefault("status", "")).trim();
        QueryWrapper<MuseumExhibitEntity> wrapper = new QueryWrapper<>();
        wrapper.and(StringUtils.isNotBlank(keyword), item -> item
                .like("name", keyword).or().like("exhibition", keyword).or().like("category", keyword));
        wrapper.eq(StringUtils.isNotBlank(status), "status", status);
        IPage<MuseumExhibitEntity> page = baseDao.selectPage(getPage(params, "update_date", false), wrapper);
        return new PageData<>(page.getRecords(), page.getTotal());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public MuseumExhibitEntity create(MuseumExhibitEntity entity) {
        validateEditable(entity);
        entity.setId(null);
        entity.setStatus(DRAFT);
        entity.setPublishedAt(null);
        entity.setSort(entity.getSort() == null ? 0 : entity.getSort());
        entity.setCreator(null);
        entity.setUpdater(null);
        entity.setCreateDate(null);
        entity.setUpdateDate(null);
        baseDao.insert(entity);
        return entity;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public MuseumExhibitEntity update(String id, MuseumExhibitEntity input) {
        MuseumExhibitEntity current = requireOne(id);
        if (PUBLISHED.equals(current.getStatus())) {
            throw new RenException("已发布展品请先下线再编辑");
        }
        validateEditable(input);
        input.setId(id);
        input.setStatus(current.getStatus());
        input.setPublishedAt(current.getPublishedAt());
        input.setCreator(current.getCreator());
        input.setCreateDate(current.getCreateDate());
        input.setUpdater(null);
        input.setUpdateDate(new Date());
        baseDao.updateById(input);
        return requireOne(id);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public MuseumExhibitEntity changeStatus(String id, String status) {
        if (!PUBLISHED.equals(status) && !OFFLINE.equals(status) && !DRAFT.equals(status)) {
            throw new RenException("不支持的展品状态");
        }
        MuseumExhibitEntity entity = requireOne(id);
        if (PUBLISHED.equals(status)) {
            validatePublishable(entity);
            entity.setPublishedAt(new Date());
        }
        entity.setStatus(status);
        entity.setUpdateDate(new Date());
        baseDao.updateById(entity);
        return entity;
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void deleteDraft(String id) {
        MuseumExhibitEntity entity = requireOne(id);
        if (PUBLISHED.equals(entity.getStatus())) {
            throw new RenException("已发布展品请先下线再删除");
        }
        baseDao.deleteById(id);
    }

    @Override
    public Map<String, Object> publicCatalog() {
        QueryWrapper<MuseumExhibitEntity> wrapper = new QueryWrapper<>();
        wrapper.eq("status", PUBLISHED).orderByAsc("sort").orderByDesc("published_at");
        List<MuseumExhibitEntity> records = baseDao.selectList(wrapper);
        List<Map<String, Object>> exhibits = new ArrayList<>();
        Date latest = null;
        for (MuseumExhibitEntity entity : records) {
            exhibits.add(toPublicExhibit(entity));
            if (entity.getPublishedAt() != null && (latest == null || entity.getPublishedAt().after(latest))) {
                latest = entity.getPublishedAt();
            }
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("version", contentVersion(exhibits));
        result.put("published_at", latest == null ? Instant.EPOCH.toString() : latest.toInstant().toString());
        result.put("content_source", "remote");
        result.put("exhibits", exhibits);
        return result;
    }

    private Map<String, Object> toPublicExhibit(MuseumExhibitEntity entity) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("id", entity.getId());
        item.put("name", entity.getName());
        item.put("era", entity.getEra());
        item.put("material", entity.getMaterial());
        item.put("category", entity.getCategory());
        item.put("summary", entity.getSummary());
        item.put("image_key", "");
        item.put("image_url", entity.getImageUrl());
        item.put("image_sha256", entity.getImageSha256());
        item.put("tags", safeList(entity.getTags()));
        item.put("observations", safeList(entity.getObservations()));
        item.put("sources", safeList(entity.getSources()));
        item.put("publication_status", "published");
        return item;
    }

    private String contentVersion(List<Map<String, Object>> exhibits) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(objectMapper.writeValueAsString(exhibits).getBytes(StandardCharsets.UTF_8));
            StringBuilder value = new StringBuilder();
            for (int index = 0; index < 8; index++) {
                value.append(String.format("%02x", digest[index]));
            }
            return value.toString();
        } catch (Exception error) {
            throw new RenException("生成馆藏版本失败");
        }
    }

    private MuseumExhibitEntity requireOne(String id) {
        MuseumExhibitEntity entity = baseDao.selectById(id);
        if (entity == null) {
            throw new RenException("展品不存在");
        }
        return entity;
    }

    private void validateEditable(MuseumExhibitEntity entity) {
        if (entity == null || StringUtils.isBlank(entity.getName()) || StringUtils.isBlank(entity.getMuseum())
                || StringUtils.isBlank(entity.getSummary()) || StringUtils.isBlank(entity.getEra())
                || StringUtils.isBlank(entity.getMaterial()) || StringUtils.isBlank(entity.getCategory())) {
            throw new RenException("博物馆、名称、年代、材质、类别和摘要不能为空");
        }
        if (entity.getName().length() > 120 || entity.getSummary().length() > 1200) {
            throw new RenException("展品名称或摘要超过长度限制");
        }
    }

    private void validatePublishable(MuseumExhibitEntity entity) {
        validateEditable(entity);
        if (StringUtils.isBlank(entity.getImageUrl())) {
            throw new RenException("发布前必须填写公开图片地址");
        }
        if (!entity.getImageUrl().startsWith("https://") && !entity.getImageUrl().startsWith("/")) {
            throw new RenException("公开图片仅支持 HTTPS 或站内相对地址");
        }
        if (entity.getSources() == null || entity.getSources().isEmpty()) {
            throw new RenException("发布前必须至少填写一条资料来源");
        }
        for (Map<String, String> source : entity.getSources()) {
            if (source == null || StringUtils.isBlank(source.get("title")) || StringUtils.isBlank(source.get("excerpt"))) {
                throw new RenException("资料来源名称和公开摘录不能为空");
            }
        }
    }

    private List<?> safeList(List<?> value) {
        return value == null ? List.of() : value;
    }
}

package xiaozhi.modules.museum.service;

import java.util.Map;

import xiaozhi.common.page.PageData;
import xiaozhi.common.service.BaseService;
import xiaozhi.modules.museum.entity.MuseumExhibitEntity;

public interface MuseumExhibitService extends BaseService<MuseumExhibitEntity> {
    PageData<MuseumExhibitEntity> page(Map<String, Object> params);
    MuseumExhibitEntity create(MuseumExhibitEntity entity);
    MuseumExhibitEntity update(String id, MuseumExhibitEntity entity);
    MuseumExhibitEntity changeStatus(String id, String status);
    void deleteDraft(String id);
    Map<String, Object> publicCatalog();
}

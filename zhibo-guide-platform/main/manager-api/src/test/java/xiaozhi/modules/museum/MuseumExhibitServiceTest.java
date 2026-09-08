package xiaozhi.modules.museum;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.Date;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import com.fasterxml.jackson.databind.ObjectMapper;

import xiaozhi.common.exception.RenException;
import xiaozhi.modules.museum.dao.MuseumExhibitDao;
import xiaozhi.modules.museum.entity.MuseumExhibitEntity;
import xiaozhi.modules.museum.service.impl.MuseumExhibitServiceImpl;

class MuseumExhibitServiceTest {
    private MuseumExhibitDao dao;
    private MuseumExhibitServiceImpl service;

    @BeforeEach
    void setUp() {
        dao = mock(MuseumExhibitDao.class);
        service = new MuseumExhibitServiceImpl(new ObjectMapper());
        ReflectionTestUtils.setField(service, "baseDao", dao);
    }

    @Test
    void createAlwaysStartsAsDraft() {
        MuseumExhibitEntity input = validExhibit();
        input.setStatus("PUBLISHED");
        when(dao.insert(any())).thenReturn(1);

        MuseumExhibitEntity created = service.create(input);

        assertEquals("DRAFT", created.getStatus());
        verify(dao).insert(created);
    }

    @Test
    void publishRequiresPublicImageAndSource() {
        MuseumExhibitEntity input = validExhibit();
        input.setImageUrl("");
        when(dao.selectById("exhibit-1")).thenReturn(input);

        assertThrows(RenException.class, () -> service.changeStatus("exhibit-1", "PUBLISHED"));
    }

    @Test
    void publishedContentMustBeTakenOfflineBeforeEditing() {
        MuseumExhibitEntity current = validExhibit();
        current.setId("exhibit-1");
        current.setStatus("PUBLISHED");
        when(dao.selectById("exhibit-1")).thenReturn(current);

        assertThrows(RenException.class, () -> service.update("exhibit-1", validExhibit()));
    }

    @Test
    @SuppressWarnings("unchecked")
    void publicCatalogOnlyContainsVisitorFields() {
        MuseumExhibitEntity published = validExhibit();
        published.setId("exhibit-1");
        published.setStatus("PUBLISHED");
        published.setPublishedAt(new Date(1_700_000_000_000L));
        published.setCreator(10001L);
        when(dao.selectList(any())).thenReturn(List.of(published));

        Map<String, Object> catalog = service.publicCatalog();
        List<Map<String, Object>> exhibits = (List<Map<String, Object>>) catalog.get("exhibits");

        assertEquals("remote", catalog.get("content_source"));
        assertNotNull(catalog.get("version"));
        assertEquals("exhibit-1", exhibits.get(0).get("id"));
        assertFalse(exhibits.get(0).containsKey("creator"));
        assertFalse(exhibits.get(0).containsKey("updateDate"));
    }

    private MuseumExhibitEntity validExhibit() {
        MuseumExhibitEntity value = new MuseumExhibitEntity();
        value.setMuseum("湖南省博物馆");
        value.setExhibition("长沙马王堆汉墓陈列");
        value.setName("素纱单衣");
        value.setEra("西汉");
        value.setMaterial("丝织物");
        value.setCategory("服饰工艺");
        value.setSummary("游客端公开摘要");
        value.setImageUrl("https://cdn.example.com/exhibit.webp");
        value.setTags(List.of("马王堆精选"));
        value.setObservations(List.of(Map.of("title", "观察衣身", "detail", "留意织物的轻薄程度")));
        value.setSources(List.of(Map.of("title", "馆方资料", "excerpt", "公开资料摘录", "status", "verified")));
        return value;
    }
}

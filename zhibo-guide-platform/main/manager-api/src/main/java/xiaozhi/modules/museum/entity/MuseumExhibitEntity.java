package xiaozhi.modules.museum.entity;

import java.util.Date;
import java.util.List;
import java.util.Map;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName(value = "museum_exhibit", autoResultMap = true)
@Schema(description = "博物馆展品内容")
public class MuseumExhibitEntity {
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    private String museum;
    private String exhibition;
    private String name;
    private String era;
    private String material;
    private String category;
    private String summary;
    private String imageUrl;
    private String imageSha256;

    @TableField(typeHandler = JacksonTypeHandler.class)
    private List<String> tags;

    @TableField(typeHandler = JacksonTypeHandler.class)
    private List<Map<String, String>> observations;

    @TableField(typeHandler = JacksonTypeHandler.class)
    private List<Map<String, String>> sources;

    private String status;
    private Integer sort;
    private Date publishedAt;

    @TableField(fill = FieldFill.INSERT)
    private Long creator;
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Long updater;
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private Date updateDate;
}
